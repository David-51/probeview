#!/usr/bin/env python3
"""probe.py — Step 3: find the supercamera endoscope and prove we can claim it.

Isolated from frame-reading on purpose: this only confirms the device is present
on USB and that libusb lets us claim the streaming interface (interface 1). If
this fails, nothing downstream can work.

Run:  .venv/bin/python probe.py
"""
import sys

import usb.core
import usb.util
import usb.backend.libusb1

# Confirmed on this Mac via ioreg: Geek szitman "supercamera" = 2ce3:3828.
# The vendor also ships a 0329:2022 variant; check both.
KNOWN_DEVICES = [(0x2CE3, 0x3828), (0x0329, 0x2022)]
HOMEBREW_DYLIB = "/opt/homebrew/lib/libusb-1.0.dylib"
STREAM_INTERFACE = 1


def get_backend():
    """Default backend works on this machine; fall back to the Homebrew dylib
    explicitly if pyusb can't find libusb on its own (classic Apple-Silicon trap)."""
    backend = usb.backend.libusb1.get_backend()
    if backend is None:
        backend = usb.backend.libusb1.get_backend(
            find_library=lambda _: HOMEBREW_DYLIB
        )
    if backend is None:
        sys.exit("FATAL: no libusb backend. Is libusb installed? brew install libusb")
    return backend


def main():
    backend = get_backend()

    dev = None
    for vid, pid in KNOWN_DEVICES:
        dev = usb.core.find(idVendor=vid, idProduct=pid, backend=backend)
        if dev is not None:
            break

    if dev is None:
        sys.exit(
            "FATAL: no supercamera device found.\n"
            "Checked: " + ", ".join(f"{v:04x}:{p:04x}" for v, p in KNOWN_DEVICES) + "\n"
            "Re-seat the cable (must be a DATA cable, not charge-only) and confirm the\n"
            "macOS 'Allow accessory to connect' approval."
        )

    print(f"device found: {dev.idVendor:04x}:{dev.idProduct:04x}  bus={dev.bus} addr={dev.address}")
    for label, attr in (("manufacturer", "manufacturer"), ("product", "product"),
                        ("serial", "serial_number")):
        try:
            print(f"  {label}: {getattr(dev, attr)}")
        except Exception as e:
            print(f"  {label}: <unreadable: {e}>")

    # Claim the streaming interface. Non-UVC => macOS holds no kernel driver, so
    # the claim should succeed. Surface any ACCESS/BUSY error verbatim.
    try:
        if dev.is_kernel_driver_active(STREAM_INTERFACE):
            dev.detach_kernel_driver(STREAM_INTERFACE)
    except Exception:
        pass

    try:
        dev.set_configuration()
        usb.util.claim_interface(dev, STREAM_INTERFACE)
        print(f"interface {STREAM_INTERFACE} claimed OK")
    except usb.core.USBError as e:
        sys.exit(f"FATAL: could not claim interface {STREAM_INTERFACE}: {e}")
    finally:
        try:
            usb.util.release_interface(dev, STREAM_INTERFACE)
            usb.util.dispose_resources(dev)
        except Exception:
            pass

    print("GATE 3: PASS")


if __name__ == "__main__":
    main()
