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

Step 4 **and** Step 5 pass with **full, untruncated 640×480 frames**. Sustained
stream ~15.5 FPS, 0 decode failures, 0 USB errors. Step 6 is blocked only by a
missing one-time dependency (OBS Virtual Camera), not by the device or our code.

> The PyPI `supercamera` package produced half-gray, truncated frames. We replaced
> its reader with [`upp_camera.py`](upp_camera.py), a correct port of the protocol —
> see **How it works**.

## Confirmed hardware

| Field | Value |
|-------|-------|
| VID:PID | `2ce3:3828` (not the alternate `0329:2022`) |
| USB names | Geek szitman / supercamera |
| Serial | redacted — your unit reports its own |
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

`upp_camera.py` drives the device directly over libusb (pyusb), ported from the
hbens C++ PoC and verified against this hardware with `diag.py`.

**Init:** claim interfaces 0 and 1, drain the iAP heartbeat, set interface 1 to
alt-setting 1, `clear_halt` the bulk OUT endpoint, send `MAGIC_INIT`
(`FF 55 FF 55 EE 10`) on iAP OUT (`0x02`) and `CONNECT_CMD` (`BB AA 05 00 00`) on
bulk OUT (`0x01`), then read bulk IN (`0x81`).

**Framing** — each USB packet is `[5-byte USB header][7-byte cam header][JPEG chunk]`:

| Field | Bytes | Notes |
|-------|-------|-------|
| magic | 2 (LE) | `0xBBAA` (`AA BB` on the wire) |
| cid | 1 | camera id, `7` or `11` — device splits each frame's head/tail across both |
| length | 2 (LE) | cam header + payload (not the 5-byte USB header) |
| fid | 1 | **frame id — frame boundary marker** |
| cam_num, flags, g_sensor | 6 | flags bit 1 = button press |

Read **one packet per bulk transfer** (`0x400` bytes), accept `cid ∈ {7,11}`, append
the payload (from offset 12), and **emit a frame when `fid` changes**. The first two
frames after connect are partial and discarded.

**Why not the PyPI package:** [`supercamera`](https://github.com/Revise-Robotics/supercamera-endoscope)
v0.1.0 reads 64 KB at once and reassembles by scanning for `FFD8`/`FFD9`, stripping
only the *leading* 12-byte header. Each 64 KB read coalesces dozens of packets whose
*interior* headers stay embedded in the JPEG → truncated, half-gray frames and
`premature end of data segment` warnings. Reassembling by `fid` from 1 KB packets
fixes it completely.

Reference decodes (cloned to `reference/`, gitignored): `hbens/geek-szitman-supercamera`
(C++ PoC — the framing we ported), `MAkcanca/useeplus-linux-driver` (kernel driver),
`jmz3/EndoscopeCamera`, `supercamera-endoscope` (PyPI source).

## Shareable app

`app.py` is a Tkinter GUI (live view + Save Frame button) packaged into a
double-clickable `ProbeView.app` with PyInstaller. The libusb dylib is bundled
inside the app, so recipients need neither Homebrew nor Python. Apple Silicon only.

Build:

```bash
source .venv/bin/activate
pyinstaller --windowed --noconfirm --clean --name ProbeView \
  --add-binary "$(readlink -f /opt/homebrew/lib/libusb-1.0.dylib):." app.py
# package for sharing (ditto preserves the bundle)
ditto -c -k --sequesterRsrc --keepParent dist/ProbeView.app ProbeView.zip
```

`upp_camera._backend()` detects the frozen bundle (`sys.frozen`) and loads the
bundled `libusb-1.0.0.dylib` from `Contents/Frameworks`. The app is **unsigned** —
recipients right-click → Open the first time to clear Gatekeeper (see
`dist/README-OPEN-ME-FIRST.txt`). `ProbeView.spec` is the saved build recipe;
`build/`, `dist/`, and `*.app` are gitignored. Saved frames land in
`~/Desktop/ProbeView/`.

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
- **Frames stream sideways** (90° rotated) — the sensor's native orientation is
  portrait. Left raw by choice; rotate downstream if you want upright.
- The old `Corrupt JPEG data: premature end of data segment` flood and half-gray
  frames came entirely from the PyPI package's reassembler; `upp_camera.py` removes
  both.

## Files

- `upp_camera.py` — the corrected protocol reader (`Camera` API). All scripts use it.
- `probe.py` — find device, claim interface 1.
- `grab.py` — save one JPEG (minimum proof).
- `view.py` — live OpenCV preview + `--headless` throughput test.
- `vcam.py` — virtual-camera bridge (needs OBS).
- `diag.py` — protocol-framing verification tool used to confirm the packet layout.
- `docs/useeplus-protocol.md` — full protocol spec, framing table, and the package bug.
- `requirements.txt` — pinned deps.

## Acknowledgements

This work stands on prior reverse-engineering of `com.useeplus.protocol`:

- [**hbens/geek-szitman-supercamera**](https://github.com/hbens/geek-szitman-supercamera)
  — the CC0 C++ proof-of-concept whose packet framing (`fid`-delimited reassembly)
  `upp_camera.py` ports.
- [**MAkcanca/useeplus-linux-driver**](https://github.com/MAkcanca/useeplus-linux-driver)
  — Linux kernel driver (MIT).
- [**jmz3/EndoscopeCamera**](https://github.com/jmz3/EndoscopeCamera) — C++/Python viewer.
- [**Revise-Robotics/supercamera-endoscope**](https://github.com/Revise-Robotics/supercamera-endoscope)
  — the PyPI `supercamera` package.

## Disclaimer

Unofficial. Not affiliated with or endorsed by the device manufacturer or any
trademark holder. "Geek szitman", "supercamera", and "USeePlus" are referenced for
interoperability only. Provided as-is for personal and educational use.

## License

[MIT](LICENSE) © 2026 Everitt Chase.
