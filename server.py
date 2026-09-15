#!/usr/bin/env python3
"""server.py — watch the endoscope from any browser on the local network.

One capture thread owns the camera (and reopens it if it is unplugged); every HTTP
client gets the latest JPEG as an MJPEG stream. Standard library only on top of the
project's existing deps.

Routes:
    /              viewer page (rotate, fullscreen, snapshot)
    /stream.mjpg   multipart MJPEG stream (also works in VLC / OBS)
    /snapshot.jpg  latest frame
    /status.json   {"connected", "fps", "resolution", "mode", "frames"}

Run:  .venv/bin/python server.py [--port 8080] [--host 0.0.0.0]
Then open http://<this Mac's LAN IP>:8080 (the URLs are printed at startup).
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from upp_camera import Camera, list_devices

BOUNDARY = "probeviewframe"

PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ProbeView</title>
<style>
  html, body { margin: 0; height: 100%; background: #111; color: #ddd;
               font: 14px -apple-system, system-ui, sans-serif; }
  body { display: flex; flex-direction: column; }
  #view { flex: 1; display: flex; align-items: center; justify-content: center;
          overflow: hidden; min-height: 0; }
  #img { flex: none; object-fit: contain; transition: transform .2s; }
  #bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
         padding: 8px 12px; background: #1c1c1c; }
  button, a.btn { background: #333; color: #eee; border: 0; border-radius: 6px;
                  padding: 8px 12px; font: inherit; text-decoration: none; cursor: pointer; }
  button:hover, a.btn:hover { background: #444; }
  #status { margin-left: auto; color: #999; }
  .off { color: #e66 !important; }
</style></head><body>
<div id="view"><img id="img" src="/stream.mjpg" alt="flux endoscope"></div>
<div id="bar">
  <button id="rot">Pivoter</button>
  <button id="fs">Plein écran</button>
  <a class="btn" id="snap" href="/snapshot.jpg" download>Capture</a>
  <span id="status">…</span>
</div>
<script>
  const img = document.getElementById("img"), st = document.getElementById("status");
  let rot = +(localStorage.getItem("rot") || 0);
  const view = document.getElementById("view");
  // Fill the view (upscaling 640x480 too); swap the box when rotated a quarter turn.
  const applyRot = () => {
    const w = view.clientWidth, h = view.clientHeight, q = rot % 180 !== 0;
    img.style.width = (q ? h : w) + "px";
    img.style.height = (q ? w : h) + "px";
    img.style.transform = `rotate(${rot}deg)`;
  };
  applyRot();
  window.addEventListener("resize", applyRot);
  document.getElementById("rot").onclick = () => {
    rot = (rot + 90) % 360; try { localStorage.setItem("rot", rot); } catch (e) {} applyRot();
  };
  document.getElementById("fs").onclick = () =>
    (document.fullscreenElement ? document.exitFullscreen()
                                : document.documentElement.requestFullscreen());
  document.getElementById("snap").onclick = (e) => {
    e.currentTarget.download = "endoscope-" + new Date().toISOString().replace(/[:.]/g, "-") + ".jpg";
  };
  // Reconnect the stream if it breaks (camera replugged, server restarted).
  img.onerror = () => setTimeout(() => { img.src = "/stream.mjpg?t=" + Date.now(); }, 1000);
  async function poll() {
    try {
      const s = await (await fetch("/status.json", {cache: "no-store"})).json();
      st.textContent = s.connected
        ? `En direct · ${s.resolution[0]}×${s.resolution[1]} · ${s.fps.toFixed(1)} FPS`
        : "Caméra non connectée";
      st.className = s.connected ? "" : "off";
    } catch (e) { st.textContent = "Serveur injoignable"; st.className = "off"; }
    setTimeout(poll, 1000);
  }
  poll();
</script></body></html>
"""


class FrameHub:
    """Latest-JPEG mailbox read by the HTTP handler. Fed by Capture below, or by the
    desktop app (app.py) when it broadcasts its own frames."""

    def __init__(self):
        self.cond = threading.Condition()
        self.jpeg = None
        self.seq = 0
        self.connected = False
        self.mode = None
        self.resolution = (0, 0)
        self.fps = 0.0
        self.running = True

    def publish(self, jpeg):
        with self.cond:
            self.jpeg = jpeg
            self.seq += 1
            self.cond.notify_all()

    def wait_frame(self, last_seq, timeout=2.0):
        """Block until a frame newer than last_seq exists; return (seq, jpeg) or (last_seq, None)."""
        with self.cond:
            self.cond.wait_for(lambda: self.seq != last_seq, timeout=timeout)
            if self.seq == last_seq:
                return last_seq, None
            return self.seq, self.jpeg


class Capture(FrameHub):
    """Owns the camera on a background thread and publishes the latest JPEG."""

    def __init__(self, index=0):
        super().__init__()
        self.index = index
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            if not list_devices():
                self._set_disconnected()
                time.sleep(1.0)
                continue
            try:
                with Camera(index=self.index) as cam:
                    self.connected, self.mode, self.resolution = True, cam.mode, cam.resolution
                    print(f"camera connected: mode={cam.mode} resolution={cam.resolution}",
                          flush=True)
                    self._stream(cam)
            except Exception as e:
                print(f"camera error: {e}", flush=True)
            self._set_disconnected()
            time.sleep(1.0)

    def _stream(self, cam):
        misses = 0
        t_last = time.monotonic()
        while self.running:
            jpeg = cam.read_jpeg()
            if jpeg is None:
                misses += 1
                if misses >= 2:      # ~2 x read timeout with no frame: reopen
                    return
                continue
            misses = 0
            now = time.monotonic()
            dt, t_last = now - t_last, now
            if dt > 0:
                self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt) if self.fps else 1.0 / dt
            self.publish(jpeg)

    def _set_disconnected(self):
        if self.connected:
            print("camera disconnected, waiting…", flush=True)
        self.connected = False
        self.fps = 0.0


def make_handler(capture):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", PAGE.encode())
            elif path == "/stream.mjpg":
                self._stream()
            elif path == "/snapshot.jpg":
                jpeg = capture.jpeg
                if jpeg is None or not capture.connected:
                    self._send(503, "text/plain; charset=utf-8", "no frame yet".encode())
                else:
                    self._send(200, "image/jpeg", jpeg)
            elif path == "/status.json":
                body = json.dumps({
                    "connected": capture.connected, "fps": round(capture.fps, 1),
                    "resolution": list(capture.resolution), "mode": capture.mode,
                    "frames": capture.seq,
                }).encode()
                self._send(200, "application/json", body)
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found")

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            seq = -1
            try:
                while capture.running:
                    seq, jpeg = capture.wait_frame(seq)
                    if jpeg is None:
                        continue
                    self.wfile.write(
                        f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                        + jpeg + b"\r\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass

    return Handler


def lan_addresses():
    """This Mac's IPv4 LAN addresses, most useful first: the default-route interface,
    then the others; link-local 169.254.x (USB/Thunderbolt links, unreachable from a
    phone) last. Read from the system configuration, without opening any socket (a
    probe connection would trigger macOS's Local Network permission prompt)."""
    import re
    import subprocess

    def run(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
        except (OSError, subprocess.SubprocessError):
            return ""

    addrs = []
    iface = re.search(r"interface:\s*(\S+)", run("route", "-n", "get", "default"))
    if iface:
        addrs += run("ipconfig", "getifaddr", iface.group(1)).split()
    addrs += re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", run("ifconfig"))
    unique = [a for i, a in enumerate(addrs)
              if a not in addrs[:i] and not a.startswith(("127.", "0."))]
    return sorted(unique, key=lambda a: a.startswith("169.254."))   # stable sort


def serve_in_background(hub, host="0.0.0.0", port=8080, tries=10):
    """Start an HTTP server for hub on the first free port from `port`, in a daemon
    thread. Returns (server, port). Stop with hub.running = False, server.shutdown()."""
    last = None
    for p in range(port, port + tries):
        try:
            server = ThreadingHTTPServer((host, p), make_handler(hub))
        except OSError as e:
            last = e
            continue
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, p
    raise OSError(f"no free port in {port}-{port + tries - 1}: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0",
                    help="bind address (0.0.0.0 = whole LAN, 127.0.0.1 = this Mac only)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--index", type=int, default=0)
    args = ap.parse_args()

    capture = Capture(index=args.index)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(capture))
    server.daemon_threads = True

    print(f"ProbeView server listening on {args.host}:{args.port}")
    print(f"  this Mac : http://localhost:{args.port}")
    if args.host in ("0.0.0.0", ""):
        for ip in lan_addresses():
            print(f"  LAN      : http://{ip}:{args.port}")
    print("Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping…")
    finally:
        capture.running = False
        server.server_close()
        time.sleep(1.2)   # let the capture thread release the camera cleanly


if __name__ == "__main__":
    main()
