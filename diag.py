#!/usr/bin/env python3
"""diag.py — confirm the real UPP packet framing against the device.

Ports the init from the C++ PoC, reads 1024-byte packets, parses the per-packet
12-byte header (5-byte USB + 7-byte cam), and reassembles by frame-id (fid).
Prints what it sees so we can confirm before rewriting the reader.
"""
import time
import usb.core
import usb.util

VID, PID = 0x2CE3, 0x3828
EP_IN, EP_OUT, EP_IAP_OUT = 0x81, 0x01, 0x02
MAGIC_INIT = bytes([0xFF, 0x55, 0xFF, 0x55, 0xEE, 0x10])
CONNECT_CMD = bytes([0xBB, 0xAA, 0x05, 0x00, 0x00])
PKT = 0x400  # read one logical packet per transfer, like the C++ PoC

dev = usb.core.find(idVendor=VID, idProduct=PID)
assert dev is not None, "device not found"
for i in (0, 1):
    try:
        if dev.is_kernel_driver_active(i):
            dev.detach_kernel_driver(i)
    except Exception:
        pass
dev.set_configuration()
usb.util.claim_interface(dev, 0)
usb.util.claim_interface(dev, 1)
# drain iAP heartbeat
for _ in range(30):
    try:
        dev.read(0x82, 512, timeout=100)
    except usb.core.USBError:
        break
dev.set_interface_altsetting(interface=1, alternate_setting=1)
dev.clear_halt(EP_OUT)
dev.write(EP_IAP_OUT, MAGIC_INIT, timeout=1000)
dev.write(EP_OUT, CONNECT_CMD, timeout=1000)
time.sleep(0.3)

import cv2, numpy as np

# C++ PoC method: single buffer, accept cid in {7,11}, delimit by fid.
frames = []   # (fid, bytes)
buf = bytearray()
cur_fid = None
pkts = 0
start = time.monotonic()
while len(frames) < 10 and time.monotonic() - start < 8:
    try:
        pkt = bytes(dev.read(EP_IN, PKT, timeout=1000))
    except usb.core.USBError:
        continue
    pkts += 1
    if len(pkt) < 12 or pkt[0] != 0xAA or pkt[1] != 0xBB or pkt[2] not in (7, 11):
        continue
    length = pkt[3] | (pkt[4] << 8)
    fid = pkt[5]
    chunk = pkt[12:5 + length]
    if cur_fid is not None and fid != cur_fid and len(buf) > 0:
        frames.append((cur_fid, bytes(buf)))
        buf = bytearray()
    cur_fid = fid
    buf.extend(chunk)

print(f"packets read: {pkts}")
ok = 0
for i, (fid, data) in enumerate(frames):
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    shape = None if img is None else img.shape
    good = shape == (480, 640, 3) and data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"
    print(f"  [{i}] fid={fid:3d} bytes={len(data):6d} soi={data[:2].hex()} "
          f"eoi={data[-2:].hex()} decoded={shape} {'OK' if good else ''}")
    if good:
        ok += 1
        if ok == 1:  # save the 3rd-ish clean frame as proof
            with open("diag-frame.jpg", "wb") as f:
                f.write(data)
print(f"clean 640x480 frames: {ok}/{len(frames)}  (first 1-2 partials expected)")

usb.util.release_interface(dev, 1)
usb.util.release_interface(dev, 0)
dev.reset()
