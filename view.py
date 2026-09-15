#!/usr/bin/env python3
"""view.py — live preview in an OpenCV window.

Default: open an OpenCV window and stream until you press 'q' or ESC.
--headless N: no window; read frames for N seconds, report sustained FPS and any
              USB errors (useful to check the camera without a display).

Run:  .venv/bin/python view.py            # visible window, press q to quit
      .venv/bin/python view.py --headless 30
"""
import argparse
import sys
import time

import usb.core

from upp_camera import Camera


def headless(cam, seconds):
    frames, errors = 0, 0
    bad = 0
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        try:
            ok, frame = cam.read()
        except usb.core.USBError as e:
            errors += 1
            print(f"  USBError: {e}")
            continue
        if ok and frame is not None:
            frames += 1
        else:
            bad += 1
    elapsed = time.monotonic() - start
    fps = frames / elapsed if elapsed else 0
    print(f"frames={frames}  empty/decode-fail={bad}  usb_errors={errors}  "
          f"elapsed={elapsed:.1f}s  -> {fps:.1f} FPS")
    if frames == 0 or errors:
        sys.exit("FAIL: no frames or USB errors")
    print("OK")


def windowed(cam):
    import cv2

    win = "supercamera endoscope  (q to quit)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    frames = 0
    start = time.monotonic()
    while True:
        ok, frame = cam.read()
        if not ok or frame is None:
            continue
        frames += 1
        elapsed = time.monotonic() - start
        fps = frames / elapsed if elapsed else 0
        cv2.putText(frame, f"{fps:.1f} FPS  {cam.resolution[0]}x{cam.resolution[1]}",
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow(win, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):  # q or ESC
            break
    cv2.destroyAllWindows()
    print(f"clean exit after {frames} frames")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--headless", type=float, metavar="SECONDS",
                    help="run without a window for SECONDS and report FPS")
    args = ap.parse_args()

    with Camera(index=args.index) as cam:
        print(f"streaming serial={cam.serial_number} resolution={cam.resolution}")
        if args.headless:
            headless(cam, args.headless)
        else:
            windowed(cam)


if __name__ == "__main__":
    main()
