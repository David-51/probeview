#!/usr/bin/env python3
"""grab.py — Step 4: the minimum proof. Save one JPEG frame from the endoscope.

Uses the supercamera high-level API (it already implements the init handshake +
12-byte-header strip + FFD8..FFD9 reassembly). Writes frame-0001.jpg.

Run:  .venv/bin/python grab.py [--index N] [--out PATH]
"""
import argparse
import sys

from supercamera import Camera, list_devices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, default=0,
                    help="camera index if the variant exposes two cameras")
    ap.add_argument("--out", default="frame-0001.jpg")
    args = ap.parse_args()

    devs = list_devices()
    if not devs:
        sys.exit("FATAL: no supercamera device found (run probe.py first).")
    print(f"found {len(devs)} device(s): " + ", ".join(repr(d) for d in devs))

    with Camera(index=args.index) as cam:
        print(f"opened: {cam.idVendor if hasattr(cam,'idVendor') else ''} "
              f"serial={cam.serial_number} resolution={cam.resolution}")
        jpeg = cam.read_jpeg()
        if not jpeg:
            sys.exit("FATAL: read_jpeg() returned no frame within timeout.")
        with open(args.out, "wb") as f:
            f.write(jpeg)
        print(f"wrote {args.out}  ({len(jpeg)} bytes)")

    print("GATE 4: PASS")


if __name__ == "__main__":
    main()
