# probeCam — Geek szitman / supercamera USB endoscope on macOS

Live JPEG streaming from a non-UVC USB endoscope on an M1 Pro Mac, over libusb.
AVFoundation / QuickTime / OBS / the vendor app can't see this device — it speaks
the proprietary `com.useeplus.protocol`, not UVC. This drives it directly.

## Result

| Gate | Step | Status |
|------|------|--------|
| 0 | venv on Python 3.13.3 | ✅ |
| 1 | device identified | ✅ |
| 2 | toolchain imports | ✅ |
| 3 | device claimed | ✅ |
| 4 | one JPEG frame (minimum) | ✅ |
| 5 | live preview / sustained stream | ✅ |
| 6 | system virtual camera | ⛔ needs OBS (see below) |

Step 4 **and** Step 5 pass. Single-frame proof saved and verified at 640×480.
Sustained headless stream measured **485 frames / 30 s = 16.2 FPS, 0 USB errors**.
Step 6 is blocked only by a missing one-time dependency (OBS Virtual Camera), not by
the device or our code.

## Confirmed hardware

| Field | Value |
|-------|-------|
| VID:PID | `2ce3:3828` (not the alternate `0329:2022`) |
| USB names | Geek szitman / supercamera |
| Serial | `022018050100030` |
| Resolution | 640×480 (sensor truth, ignore "4K" marketing) |
| Sustained rate | ~16 FPS |
| Stream interface | 1 (bulk IN `0x81`, OUT `0x01`) |

## Run

```bash
source .venv/bin/activate
python probe.py            # identify + claim         (Gate 3)
python grab.py             # save frame-0001.jpg      (Gate 4)
python view.py             # live window, q to quit   (Gate 5)
python view.py --headless 30   # no-display FPS test
python vcam.py             # virtual webcam           (Gate 6, needs OBS)
```

`grab.py --index 1` / `view.py --index 1` select the second lens on two-camera
variants (long-press the device button also toggles lenses).

## How it works

The [`supercamera`](https://github.com/Revise-Robotics/supercamera-endoscope) PyPI
package (v0.1.0) already implements the init handshake and frame reassembly; our
scripts are thin wrappers around its `Camera` API. The init sequence it performs:
set interface 1 to alt-setting 1, drain the iAP heartbeat, send `MAGIC_INIT`
(`FF 55 FF 55 EE 10`) on the iAP OUT endpoint and `CONNECT_CMD` (`BB AA 05 00 00`)
on the bulk OUT endpoint, then read bulk IN, strip the 12-byte `AA BB …` packet
header, and reassemble JPEGs between `FFD8` and `FFD9`.

Reference decodes (cloned to `reference/`, gitignored): `supercamera-endoscope`
(primary), `hbens/geek-szitman-supercamera` (C++ PoC), `MAkcanca/useeplus-linux-driver`
(authoritative framing), `jmz3/EndoscopeCamera`.

## Step 6 — virtual camera prerequisite

`pyvirtualcam`'s only macOS backend is the OBS Virtual Camera. It is not installed
here, so `vcam.py` stops with a clear message. To enable: install OBS Studio 30+,
run **Tools → Start Virtual Camera** once (installs a System Extension), approve it
in **System Settings → Privacy & Security**, restart if prompted, then re-run
`vcam.py`. The endoscope then appears as "OBS Virtual Camera" in any app.

## Environment notes & traps

- **`system_profiler SPUSBDataType` returns exit 0 with zero bytes** in this
  sandboxed shell (IOKit access denied). `ioreg -p IOUSB -l -w 0` is the working
  enumeration path here — use it to confirm the device.
- **Python 3.14** (system default) lacks some wheels; the venv is built on **3.13.3**.
- **libusb** (Homebrew 1.0.30) at `/opt/homebrew/lib/libusb-1.0.dylib`. pyusb found
  the backend on its own here; `probe.py` falls back to that explicit path if not.
- **Per-frame `Corrupt JPEG data: premature end of data segment`** warnings during
  streaming are from libjpeg, non-fatal: the upstream reassembler returns at the
  first `FFD9`, which is sometimes a false marker inside entropy data, slightly
  truncating frames. They still decode and display. Cosmetic, upstream — not fixed here.

## Files

- `probe.py` — find device, claim interface 1.
- `grab.py` — save one JPEG (minimum proof).
- `view.py` — live OpenCV preview + `--headless` throughput test.
- `vcam.py` — virtual-camera bridge (needs OBS).
- `requirements.txt` — pinned deps.
