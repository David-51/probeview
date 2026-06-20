# com.useeplus.protocol — Geek szitman / supercamera endoscope

How the non-UVC USB endoscope (`2ce3:3828`) actually streams, and why the PyPI
`supercamera` package truncates frames. Ported from the hbens C++ PoC, verified
against the hardware with `diag.py`.

## Device

| Field | Value |
|-------|-------|
| VID:PID | `2ce3:3828` (alt variant `0329:2022`) |
| USB names | Geek szitman / supercamera |
| Serial (this unit) | `022018050100030` |
| Resolution | 640×480 (sensor truth; portrait — streams 90° sideways) |
| Sustained rate | ~15.5 FPS |
| Stream interface | 1, alt-setting 1 · bulk IN `0x81`, OUT `0x01` |
| iAP interface | 0 · bulk IN `0x82`, OUT `0x02` |

## Init handshake

1. Claim interfaces 0 and 1.
2. Drain pending iAP heartbeat reads on `0x82`.
3. `set_interface_altsetting(1, 1)`; `clear_halt(0x01)`.
4. Write `MAGIC_INIT` = `FF 55 FF 55 EE 10` to iAP OUT `0x02`.
5. Write `CONNECT_CMD` = `BB AA 05 00 00` to bulk OUT `0x01`.
6. Read bulk IN `0x81`. Discard the first ~2 (partial) frames.

## Packet framing

Read **one logical packet per bulk transfer** (`0x400` = 1024 bytes). Layout:

```
[ 5-byte USB header ][ 7-byte cam header ][ JPEG payload chunk ]
```

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0 | magic | 2 (LE) | `0xBBAA` → wire bytes `AA BB` |
| 2 | cid | 1 | camera id `7` or `11`; both belong to the SAME frame |
| 3 | length | 2 (LE) | cam header + payload; excludes the 5-byte USB header |
| 5 | fid | 1 | **frame id — the frame boundary** |
| 6 | cam_num | 1 | |
| 7 | flags | 1 | bit0 `has_g`, **bit1 `button_press`**, bits2-7 other |
| 8 | g_sensor | 4 (LE) | |
| 12 | JPEG chunk | — | runs to offset `5 + length` |

**Reassembly:** single buffer; accept `cid ∈ {7, 11}`; append each packet's payload
(offset 12 → `5+length`); **emit a complete frame when `fid` changes.** A complete
frame starts `FF D8` and ends `FF D9` and decodes to 640×480. This unit splits each
frame's head and tail across cid 7 and cid 11 — both must go into one buffer.

## Why the PyPI `supercamera` package fails here

`supercamera` v0.1.0 reads **65536 bytes** per transfer and reassembles by scanning
for `FFD8`/`FFD9`, stripping only the **leading** 12-byte header. A 64 KB read
coalesces dozens of packets whose **interior** 12-byte headers stay embedded in the
JPEG stream → corrupt entropy data, a false early `FFD9`, truncated half-gray frames,
and a per-frame `Corrupt JPEG data: premature end of data segment` warning.

Reading 1 KB packets and delimiting by `fid` removes the problem entirely. The fix
lives in [`../upp_camera.py`](../upp_camera.py).

## Environment traps (this Mac)

- `system_profiler SPUSBDataType` returns exit 0 with **zero bytes** under the
  sandboxed shell (IOKit denied). Use `ioreg -p IOUSB -l -w 0` to enumerate.
- Build the venv on **Python 3.13** (3.14 lacks some wheels).
- libusb via Homebrew at `/opt/homebrew/lib/libusb-1.0.dylib`; pyusb finds it on its
  own, with an explicit `find_library` fallback in `upp_camera._backend()`.

## Reference

- `reference/geek-szitman-supercamera/supercamera_poc.cpp` — the framing we ported.
- `reference/useeplus-linux-driver/supercamera_simple.c` — kernel driver.
- `reference/EndoscopeCamera`, `reference/supercamera-endoscope` (PyPI source).
