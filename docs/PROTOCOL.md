# USB protocol notes — Geek szitman / Useeplus endoscopes (`2ce3:3828`)

Technical reference for contributors. End users only need the [README](../README.md).

These endoscopes are **not UVC webcams**. The same USB ID ships with (at least) two
firmware "personalities". [`upp_camera.py`](../upp_camera.py) implements both and picks
one from the USB descriptors.

| | JPEG personality | YUV personality (i4season) |
|---|---|---|
| Seen as | product `supercamera` | product `useepluscam`, bcdDevice `1.11` |
| Firmware | — | `su4p-002`, `5.0.13` |
| Interface 1 (`com.useeplus.protocol`, alt 1) | bulk IN `0x81`, OUT `0x01` | bulk IN `0x82`, OUT `0x02` |
| Interface 0 (iAP) | bulk IN `0x82`, OUT `0x02` | bulk IN `0x81`, OUT `0x01` |
| Start | bulk commands (`FF 55…`, `BB AA 05`) | class control requests on EP0 |
| Frames | JPEG split in ~1 KB packets | raw YUYV 4:2:2 |
| Resolution / rate | 640×480, ~15 FPS | 640×480, ~15 FPS |

Detection rule used by `upp_camera.personality()`: if the vendor interface with
`bInterfaceProtocol == 1` has IN endpoint `0x81` → JPEG, otherwise → YUV.

---

## YUV personality (i4season)

Documented first by [technicallyvu/usb-scope](https://github.com/technicallyvu/usb-scope)
(spec §12) and confirmed on hardware here.

### Start / stop

All requests: class type, device recipient, endpoint 0, `wValue = 5`, `wIndex = 0`.

| Step | bmRequestType | bRequest | Data | Notes |
|------|---------------|----------|------|-------|
| Info | `0xA0` | `0` | read 512 | 480-byte block, see below |
| Start | `0x20` | `1` | 64 zero bytes | stream begins on bulk IN `0x82` |
| Stop | `0x20` | `2` | none | |

Before starting: claim interface 1 and select alt-setting 1. **Do not touch interface
0**: on macOS `accessoryd` holds it, and bulk writes there time out and make the
device drop off the bus. Other `wValue`/`bRequest` combinations STALL or, worse, can
crash the firmware until it is replugged — don't probe blindly.

Info block (observed):

| Offset | Content | Example |
|--------|---------|---------|
| 0 | `01` | |
| 1..16 | vendor (C string) | `i4season` |
| 17..32 | product | `su4p-002` |
| 33..40 | firmware | `5.0.13` |
| 46..47 | width, LE | `640` |
| 48..49 | height, LE | `480` |

Only one resolution is advertised.

### Stream

```
[511-byte header][width × height × 2 bytes YUYV (Y0 U Y1 V)]  repeated
header = DD CC 01 00 60 09 00 <flags> 00 … (constant)
flags bit 1 = camera button pressed
```

The 511-byte header is a USB short packet, so each bulk transfer ends right after it.
**Read with a large buffer (1 MiB)**: each transfer then returns exactly
`[frame payload][next header]` — no loss at ~15 FPS. With 16 KB reads, Python can't
drain the endpoint fast enough and the device drops data (frames of varying length).
The reader still resynchronises on the `DD CC 01 00` magic and discards any frame
whose payload length isn't exactly `width × height × 2`.

### About "1920×1440 / 2 MP"

The vendor apps save 1920×1440 photos and H.264 videos, but these are 3× upscales of
the 640×480 stream: the firmware advertises only 640×480, each frame carries exactly
614 400 bytes, raw 1920×1440 at 15 FPS would not fit USB 2.0, and downscaling an app
capture to 640×480 and back loses almost nothing (PSNR peaks at 640×480).

---

## JPEG personality

Ported from the [hbens C++ PoC](https://github.com/hbens/geek-szitman-supercamera).
Not re-tested in this fork (no such unit available), kept as in the original project.

### Init handshake

1. Claim interfaces 0 and 1.
2. Drain pending iAP heartbeat reads on `0x82`.
3. `set_interface_altsetting(1, 1)`; `clear_halt(0x01)`.
4. Write `MAGIC_INIT` = `FF 55 FF 55 EE 10` to iAP OUT `0x02`.
5. Write `CONNECT_CMD` = `BB AA 05 00 00` to bulk OUT `0x01`.
6. Read bulk IN `0x81`. Discard the first ~2 (partial) frames.

Stop: `BB AA 08 00 00`. Never send `BB AA 06` mid-stream (it stalls the stream, see
[Tibiaworx/usee-plus-camera](https://github.com/Tibiaworx/usee-plus-camera)).

### Packet framing

Read **one logical packet per bulk transfer** (`0x400` = 1024 bytes):

```
[ 5-byte USB header ][ 7-byte cam header ][ JPEG payload chunk ]
```

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0 | magic | 2 (LE) | `0xBBAA` → wire bytes `AA BB` |
| 2 | cid | 1 | `7` or `11`; both belong to the SAME frame |
| 3 | length | 2 (LE) | cam header + payload; excludes the 5-byte USB header |
| 5 | fid | 1 | **frame id — the frame boundary** |
| 6 | cam_num | 1 | |
| 7 | flags | 1 | bit0 `has_g`, **bit1 `button_press`** |
| 8 | g_sensor | 4 (LE) | |
| 12 | JPEG chunk | — | runs to offset `5 + length` |

**Reassembly:** one buffer; accept `cid ∈ {7, 11}`; append each payload; **emit a
frame when `fid` changes**. A complete frame starts `FF D8`, ends `FF D9`. Frames
stream 90° sideways on this personality.

### Why the PyPI `supercamera` package fails

`supercamera` v0.1.0 reads 64 KB per transfer and reassembles by scanning for
`FFD8`/`FFD9`, stripping only the leading 12-byte header. Interior headers of the
coalesced packets stay embedded in the JPEG → truncated, half-gray frames and
`Corrupt JPEG data: premature end of data segment`. Reading 1 KB packets and
delimiting by `fid` fixes it.

---

## Tips

- On macOS, `ioreg -p IOUSB -l -w 0` lists the device; `ioreg -p IOService -t` shows
  which process holds each interface.
- libusb comes from Homebrew (`/opt/homebrew/lib/libusb-1.0.dylib`);
  `upp_camera._backend()` falls back to that path, or to a copy bundled in the app.
