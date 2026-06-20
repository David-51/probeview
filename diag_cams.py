#!/usr/bin/env python3
"""diag_cams.py — is camera switching a software filter or a hardware long-press?

Opens via upp_camera (robust), then reads raw packets off the handle and inspects
cam_num (byte 6). Reports the cam_num of every complete frame and button presses.
LONG-PRESS the device button during the run to see whether cam_num changes.
"""
import time

import cv2
import numpy as np
import usb.core

from upp_camera import Camera, EP_IN, PKT_SIZE, USB_HDR, PAYLOAD_OFFSET, VALID_CIDS

cam = Camera()
dev = cam._dev
print("Opened. Running ~20s — LONG-PRESS the device button mid-run.\n")

buf = bytearray()
cur_fid = None
cur_camnums, cur_cids = set(), set()
frame_n = 0
seen = {}
buttons = 0
start = time.monotonic()
while time.monotonic() - start < 20:
    try:
        pkt = bytes(dev.read(EP_IN, PKT_SIZE, timeout=1000))
    except usb.core.USBError:
        continue
    if len(pkt) < PAYLOAD_OFFSET or pkt[0] != 0xAA or pkt[1] != 0xBB \
            or pkt[2] not in VALID_CIDS:
        continue
    cid = pkt[2]
    length = pkt[3] | (pkt[4] << 8)
    fid = pkt[5]
    cam_num = pkt[6]
    if (pkt[7] >> 1) & 1:
        buttons += 1
    chunk = pkt[PAYLOAD_OFFSET:USB_HDR + length]
    if cur_fid is not None and fid != cur_fid and len(buf) > 0:
        data = bytes(buf)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is not None and img.shape == (480, 640, 3):
            frame_n += 1
            key = tuple(sorted(cur_camnums))
            seen[key] = seen.get(key, 0) + 1
            if frame_n <= 12 or frame_n % 20 == 0:
                print(f"frame {frame_n:4d}  cam_num={key}  cids={sorted(cur_cids)}  bytes={len(data)}")
        buf = bytearray()
        cur_camnums, cur_cids = set(), set()
    cur_fid = fid
    cur_camnums.add(cam_num)
    cur_cids.add(cid)
    buf.extend(chunk)

print(f"\ncomplete frames: {frame_n}   button-press packets: {buttons}")
print("frames grouped by cam_num set:")
for k, c in sorted(seen.items()):
    print(f"  cam_num {k}: {c} frames")
cam.release()
