#!/usr/bin/env python3
"""upp_camera.py — correct com.useeplus.protocol reader for the supercamera endoscope.

Why this exists: the PyPI `supercamera` package reassembles frames by scanning for
JPEG FFD8/FFD9 across 64 KB bulk reads, stripping only the leading 12-byte header.
This device coalesces many ~1 KB protocol packets into each bulk read, each with its
OWN 12-byte header, so interior headers stay embedded in the JPEG -> truncated /
corrupt frames (the "premature end of data segment" / half-gray image).

This module ports the protocol from the hbens C++ PoC (github.com/hbens/geek-szitman-
supercamera), verified against the device:

  packet = [5-byte USB header][7-byte cam header][JPEG payload chunk]
    USB header : magic uint16 LE = 0xBBAA, cid uint8, length uint16 LE
                 (length counts the cam header + payload, not the 5-byte USB header)
    cam header : fid uint8, cam_num uint8, flags uint8, g_sensor uint32 LE
  Read ONE packet per bulk transfer (0x400 bytes). Accept cid in {7, 11} (the device
  splits each frame's head/tail across both). Reassemble by fid: a frame is complete
  when fid changes. JPEG payload begins at offset 12.

Second firmware personality ("i4season YUV", e.g. su4p-002 fw 5.0.13, bcdDevice 1.11):
same VID:PID, but the com.useeplus.protocol interface carries bulk IN 0x82 / OUT 0x02
and ignores the BB AA commands. It is driven with class control requests on endpoint 0
(bmRequestType 0x20/0xA0, wValue 5): request 0 = 480-byte info block (width/height at
offsets 46/48), request 1 = start, request 2 = stop. The stream is raw YUYV 4:2:2:
  [511-byte header, magic DD CC 01 00, flags at byte 7][width*height*2 bytes]
The header is a short packet, so one large bulk read returns exactly one frame.
The personality is picked from the descriptors: protocol interface IN 0x81 = JPEG.

API mirrors the supercamera package so the other scripts are drop-in:
    with Camera() as cam:
        ret, frame = cam.read()    # (bool, numpy BGR ndarray)
        jpeg = cam.read_jpeg()     # JPEG bytes (encoded on the fly for YUV units)
"""
import time

import usb.core
import usb.util

KNOWN_DEVICES = [(0x2CE3, 0x3828), (0x0329, 0x2022)]
EP_OUT, EP_IN = 0x01, 0x81          # interface 1 (com.useeplus.protocol) bulk
EP_IAP_OUT, EP_IAP_IN = 0x02, 0x82  # interface 0 (iAP)
MAGIC_INIT = bytes([0xFF, 0x55, 0xFF, 0x55, 0xEE, 0x10])
CONNECT_CMD = bytes([0xBB, 0xAA, 0x05, 0x00, 0x00])

PKT_SIZE = 0x400          # one logical packet per bulk read
USB_HDR = 5               # magic(2) + cid(1) + length(2)
PAYLOAD_OFFSET = 12       # USB header(5) + cam header(7)
VALID_CIDS = (7, 11)
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"
HOMEBREW_DYLIB = "/opt/homebrew/lib/libusb-1.0.dylib"

# i4season YUV personality
YUV_INTERFACE = 1
YUV_EP_IN = 0x82
YUV_REQ_TYPE_IN, YUV_REQ_TYPE_OUT = 0xA0, 0x20
YUV_REQ_INFO, YUV_REQ_START, YUV_REQ_STOP = 0, 1, 2
YUV_WVALUE = 5
YUV_MAGIC = b"\xdd\xcc\x01\x00"
YUV_HDR = 511
YUV_READ_SIZE = 1 << 20   # > one frame: the header's short packet ends each transfer
JPEG_QUALITY = 85


def _bundled_libusb():
    """When frozen by PyInstaller the recipient has no Homebrew; the libusb dylib is
    bundled inside the app. Look for it next to the frozen executable / in _MEIPASS."""
    import os
    import sys
    if not getattr(sys, "frozen", False):
        return None
    roots = [getattr(sys, "_MEIPASS", None), os.path.dirname(sys.executable),
             os.path.join(os.path.dirname(sys.executable), "..", "Frameworks")]
    for root in roots:
        if not root:
            continue
        for name in ("libusb-1.0.0.dylib", "libusb-1.0.dylib"):
            p = os.path.join(root, name)
            if os.path.exists(p):
                return p
    return None


def _backend():
    import usb.backend.libusb1 as libusb1
    bundled = _bundled_libusb()
    if bundled:
        b = libusb1.get_backend(find_library=lambda _: bundled)
        if b is not None:
            return b
    b = libusb1.get_backend()
    if b is None:
        b = libusb1.get_backend(find_library=lambda _: HOMEBREW_DYLIB)
    return b


def personality(dev):
    """'jpeg' for the documented useeplus layout (video IN 0x81), 'yuv' otherwise."""
    for intf in dev.get_active_configuration():
        if intf.bInterfaceClass == 0xFF and intf.bInterfaceProtocol == 1:
            if any(ep.bEndpointAddress == EP_IN for ep in intf):
                return "jpeg"
    return "yuv"


def list_devices():
    found = []
    for vid, pid in KNOWN_DEVICES:
        found.extend(usb.core.find(find_all=True, idVendor=vid, idProduct=pid,
                                   backend=_backend()))
    return found


class Camera:
    def __init__(self, index=0, timeout=5.0):
        self._timeout = timeout
        self._index = index
        self._dev = None
        self._buf = bytearray()
        self._cur_fid = None
        self._frames_read = 0
        self.mode = None
        self._size = (640, 480)
        self.flags = 0            # YUV header byte 7 of the last frame (bit 1 = button)
        self._open()

    def _find(self):
        devs = list_devices()
        if not devs:
            raise RuntimeError(
                "No supercamera device found. Known IDs: "
                + ", ".join(f"{v:04x}:{p:04x}" for v, p in KNOWN_DEVICES)
            )
        if self._index >= len(devs):
            raise RuntimeError(f"index {self._index} out of range ({len(devs)} found)")
        return devs[self._index]

    def _open(self, attempts=3):
        """Open + handshake, with recovery. Back-to-back runs can catch the device
        mid-re-enumeration; on a transient USB error we reset, settle, re-find, retry."""
        last = None
        for attempt in range(attempts):
            dev = self._find()
            self._dev = dev
            try:
                self._init_device(dev)
                return
            except usb.core.USBError as e:
                last = e
                try:
                    dev.reset()           # recovery only — not a routine teardown step
                except Exception:
                    pass
                usb.util.dispose_resources(dev)
                time.sleep(1.5)           # let it re-enumerate
        raise RuntimeError(f"could not open device after {attempts} attempts: {last}")

    def _init_device(self, dev):
        self.mode = personality(dev)
        if self.mode == "yuv":
            self._init_yuv(dev)
        else:
            self._init_jpeg(dev)

    def _init_yuv(self, dev):
        # Only interface 1: on macOS accessoryd owns the iAP interface (0), and
        # writing to it makes the device drop off the bus.
        usb.util.claim_interface(dev, YUV_INTERFACE)
        dev.set_interface_altsetting(interface=YUV_INTERFACE, alternate_setting=1)
        info = bytes(dev.ctrl_transfer(YUV_REQ_TYPE_IN, YUV_REQ_INFO, YUV_WVALUE, 0,
                                       512, timeout=1000))
        if len(info) >= 50:
            w = info[46] | (info[47] << 8)
            h = info[48] | (info[49] << 8)
            if 0 < w <= 4096 and 0 < h <= 4096:
                self._size = (w, h)
        dev.ctrl_transfer(YUV_REQ_TYPE_OUT, YUV_REQ_START, YUV_WVALUE, 0, bytes(64),
                          timeout=1000)
        self._buf = bytearray()
        if self._read_yuyv() is None:
            raise usb.core.USBTimeoutError("no video after start", -7, 60)

    def _init_jpeg(self, dev):
        for intf in (0, 1):
            try:
                if dev.is_kernel_driver_active(intf):
                    dev.detach_kernel_driver(intf)
            except Exception:
                pass
        dev.set_configuration()
        usb.util.claim_interface(dev, 0)
        usb.util.claim_interface(dev, 1)
        # drain pending iAP heartbeat
        for _ in range(30):
            try:
                dev.read(EP_IAP_IN, 512, timeout=100)
            except usb.core.USBError:
                break
        dev.set_interface_altsetting(interface=1, alternate_setting=1)
        dev.clear_halt(EP_OUT)
        dev.write(EP_IAP_OUT, MAGIC_INIT, timeout=1000)
        dev.write(EP_OUT, CONNECT_CMD, timeout=1000)
        time.sleep(0.3)
        self._buf = bytearray()
        self._cur_fid = None
        # discard the first couple of (partial) frames after connect
        for _ in range(2):
            self.read_jpeg()

    def _read_yuyv(self):
        """Return one raw YUYV frame (bytes, width*height*2), or None on timeout."""
        frame_len = self._size[0] * self._size[1] * 2
        deadline = time.monotonic() + self._timeout
        while True:
            frame = self._carve_yuyv(frame_len)
            if frame is not None:
                self._frames_read += 1
                return frame
            if time.monotonic() >= deadline:
                return None
            try:
                self._buf += self._dev.read(YUV_EP_IN, YUV_READ_SIZE, timeout=1000)
            except usb.core.USBTimeoutError:
                continue

    def _carve_yuyv(self, frame_len):
        """Pop the first complete header-delimited frame from the buffer, if any."""
        buf = self._buf
        while True:
            start = buf.find(YUV_MAGIC)
            if start < 0:
                del buf[:-(len(YUV_MAGIC) - 1)]
                return None
            end = buf.find(YUV_MAGIC, start + YUV_HDR)
            if end < 0:
                del buf[:start]
                return None
            payload_len = end - start - YUV_HDR
            if payload_len == frame_len:
                self.flags = buf[start + 7]
                frame = bytes(buf[start + YUV_HDR:end])
                del buf[:end]
                return frame
            del buf[:end]   # truncated frame, or magic inside pixel data: resync

    def _yuyv_to_bgr(self, yuyv):
        import cv2
        import numpy as np
        w, h = self._size
        return cv2.cvtColor(np.frombuffer(yuyv, np.uint8).reshape(h, w, 2),
                            cv2.COLOR_YUV2BGR_YUYV)

    def read_jpeg(self):
        """Return one complete JPEG frame as bytes, or None on timeout."""
        if self.mode == "yuv":
            import cv2
            yuyv = self._read_yuyv()
            if yuyv is None:
                return None
            ok, jpeg = cv2.imencode(".jpg", self._yuyv_to_bgr(yuyv),
                                    [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            return jpeg.tobytes() if ok else None
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            try:
                pkt = bytes(self._dev.read(EP_IN, PKT_SIZE, timeout=1000))
            except usb.core.USBError:
                continue
            if len(pkt) < PAYLOAD_OFFSET or pkt[0] != 0xAA or pkt[1] != 0xBB \
                    or pkt[2] not in VALID_CIDS:
                continue
            length = pkt[3] | (pkt[4] << 8)
            fid = pkt[5]
            chunk = pkt[PAYLOAD_OFFSET:USB_HDR + length]
            if self._cur_fid is not None and fid != self._cur_fid and self._buf:
                frame = bytes(self._buf)
                self._buf = bytearray(chunk)   # seed next frame
                self._cur_fid = fid
                if frame.startswith(JPEG_SOI) and frame.endswith(JPEG_EOI):
                    self._frames_read += 1
                    return frame
                continue  # partial / corrupt boundary frame, skip
            self._buf.extend(chunk)
            self._cur_fid = fid
        return None

    def read(self):
        """Return (success, numpy BGR ndarray)."""
        if self.mode == "yuv":
            yuyv = self._read_yuyv()
            return (False, None) if yuyv is None else (True, self._yuyv_to_bgr(yuyv))
        import cv2
        import numpy as np
        jpeg = self.read_jpeg()
        if jpeg is None:
            return False, None
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        return (img is not None), img

    @property
    def resolution(self):
        return self._size

    @property
    def frames_read(self):
        return self._frames_read

    @property
    def serial_number(self):
        try:
            return self._dev.serial_number
        except Exception:
            return None

    def release(self):
        if self._dev is None:
            return
        # Stop the stream (alt 0) and release cleanly. No routine reset() — a reset
        # forces re-enumeration and makes the *next* open race; keep teardown gentle.
        if self.mode == "yuv":
            try:
                self._dev.ctrl_transfer(YUV_REQ_TYPE_OUT, YUV_REQ_STOP, YUV_WVALUE, 0,
                                        None, timeout=1000)
            except Exception:
                pass
        try:
            self._dev.set_interface_altsetting(interface=1, alternate_setting=0)
        except Exception:
            pass
        for intf in (1, 0):
            try:
                usb.util.release_interface(self._dev, intf)
            except Exception:
                pass
        try:
            usb.util.dispose_resources(self._dev)
        except Exception:
            pass
        self._dev = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.release()

    def __del__(self):
        self.release()


if __name__ == "__main__":
    # Smoke test: list devices, open, grab one frame, report.
    import sys

    devs = list_devices()
    if not devs:
        sys.exit("no supercamera device found")
    print(f"found {len(devs)} device(s): " + ", ".join(repr(d) for d in devs))
    with Camera() as cam:
        jpeg = cam.read_jpeg()
        if not jpeg:
            sys.exit("no frame within timeout")
        ok = jpeg.startswith(JPEG_SOI) and jpeg.endswith(JPEG_EOI)
        print(f"serial={cam.serial_number} mode={cam.mode} resolution={cam.resolution}")
        print(f"frame: {len(jpeg)} bytes  valid_jpeg={ok}")
        print("upp_camera.py OK")
