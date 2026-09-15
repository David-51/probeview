#!/usr/bin/env python3
"""grab.py — save one JPEG frame from the endoscope.

Run:  .venv/bin/python grab.py [--index N] [--out PATH]
"""
import argparse
import sys

from upp_camera import Camera, list_devices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, default=0,
                    help="camera index if the variant exposes two cameras")
    ap.add_argument("--out", default="frame-0001.jpg")
    args = ap.parse_args()

    devs = list_devices()
    if not devs:
        sys.exit("FATAL: no endoscope found. Is it plugged in (data cable)?")
    print(f"found {len(devs)} device(s): " + ", ".join(repr(d) for d in devs))

    with Camera(index=args.index) as cam:
        print(f"opened: serial={cam.serial_number} resolution={cam.resolution}")
        jpeg = cam.read_jpeg()
        if not jpeg:
            sys.exit("FATAL: read_jpeg() returned no frame within timeout.")
        with open(args.out, "wb") as f:
            f.write(jpeg)
        print(f"wrote {args.out}  ({len(jpeg)} bytes)")


if __name__ == "__main__":
    main()
