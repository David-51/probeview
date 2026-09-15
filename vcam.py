#!/usr/bin/env python3
"""vcam.py — expose the endoscope as a system virtual camera (via OBS).

Pipes live frames into pyvirtualcam's OBS backend so the endoscope shows up as a
selectable webcam in Zoom / Meet / Photo Booth / QuickTime.

PREREQUISITE (one-time, macOS): `pip install pyvirtualcam`, and OBS Studio 30.0+
installed with its Virtual Camera started once (Tools -> Start Virtual Camera), which
installs and activates a System Extension (approve it in System Settings > Privacy &
Security; a restart may be required). Without it pyvirtualcam raises "OBS Virtual Camera is not installed".

Run:  .venv/bin/python vcam.py        # Ctrl-C to stop
"""
import sys

import pyvirtualcam

from upp_camera import Camera

W, H, FPS = 640, 480, 20


def main():
    try:
        vcam = pyvirtualcam.Camera(width=W, height=H, fps=FPS)
    except RuntimeError as e:
        sys.exit(
            f"FATAL: virtual camera backend unavailable: {e}\n\n"
            "Install OBS Studio 30+, run Tools > Start Virtual Camera once to install\n"
            "the System Extension, approve it in System Settings > Privacy & Security,\n"
            "then re-run this script."
        )

    print(f"virtual camera up: {vcam.device}  ({W}x{H} @ {FPS}fps)")
    print("select 'OBS Virtual Camera' in any app. Ctrl-C to stop.")

    try:
        import cv2

        with Camera() as cam:
            while True:
                ok, frame = cam.read()
                if not ok or frame is None:
                    continue
                # pyvirtualcam wants RGB; cv2 gives BGR.
                vcam.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                vcam.sleep_until_next_frame()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        vcam.close()


if __name__ == "__main__":
    main()
