#!/usr/bin/env python3
"""app.py — ProbeView: double-clickable endoscope viewer.

Native (Tkinter) window: live video scaled to the window, rotation, photo, video
recording (MP4) and a status line. Capture runs on a background thread; the UI is
updated on the main thread via .after().

Photos and videos go to ~/Desktop/ProbeView. The rotation is remembered.

Keys: Space = photo, R = rotate, V = start/stop recording.
"""
import json
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk

from upp_camera import Camera, list_devices

SAVE_DIR = os.path.expanduser("~/Desktop/ProbeView")
SETTINGS = os.path.expanduser("~/Library/Application Support/ProbeView/settings.json")
REC_FPS = 15                 # camera delivers ~15 FPS
PHOTO_QUALITY = 95
ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
             270: cv2.ROTATE_90_COUNTERCLOCKWISE}

BG, FG, DIM, RED = "#1e1e1e", "#cccccc", "#888888", "#ff5555"


def load_settings():
    try:
        with open(SETTINGS) as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        with open(SETTINGS, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


class ProbeViewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ProbeView")
        self.root.configure(bg=BG)
        self.root.minsize(560, 420)
        self.root.geometry("900x720")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Button bar pinned to the bottom; video fills the rest and scales with it.
        bar = tk.Frame(root, bg=BG)
        bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # The video area's size comes from the window, never from the image: a Label
        # that sizes itself to its image would grow a few pixels per refresh.
        self.view = tk.Frame(root, bg="#000000")
        self.view.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 6))
        self.view.pack_propagate(False)
        self.video = tk.Label(self.view, bg="#000000", bd=0, highlightthickness=0)
        self.video.place(relx=0.5, rely=0.5, anchor="center")

        self.rot_btn = tk.Button(bar, text="↻ Pivoter", command=self.rotate, width=9)
        self.photo_btn = tk.Button(bar, text="Photo", command=self.take_photo, width=7)
        self.rec_btn = tk.Button(bar, text="● Enregistrer", command=self.toggle_recording,
                                 width=11)
        self.dir_btn = tk.Button(bar, text="Dossier", command=self.open_folder, width=7)
        for b in (self.rot_btn, self.photo_btn, self.rec_btn, self.dir_btn):
            b.pack(side="left", padx=(0, 6))
        self.photo_btn.config(state="disabled")
        self.rec_btn.config(state="disabled")
        self.status = tk.Label(bar, text="Connexion…", fg=FG, bg=BG, anchor="w")
        self.status.pack(side="left", padx=8)

        root.bind("<space>", lambda e: self.take_photo())
        root.bind("<Key-r>", lambda e: self.rotate())
        root.bind("<Key-v>", lambda e: self.toggle_recording())

        self.settings = load_settings()
        self.rotation = self.settings.get("rotation", 0) % 360
        self.cam = None
        self.frame = None            # latest frame, rotated, BGR
        self.imgtk = None
        self.running = True
        self.frames = 0
        self.fps = 0.0
        self._fps_mark = (time.monotonic(), 0)
        self.message, self.message_until = None, 0.0

        self.rec_lock = threading.Lock()
        self.writer = None
        self.rec_path = None
        self.rec_start = 0.0
        self.rec_written = 0

        # Open the camera on a worker so the window paints immediately.
        threading.Thread(target=self._open_camera, daemon=True).start()
        self._tick()

    # ----------------------------------------------------------------- camera
    def _open_camera(self):
        if not list_devices():
            self.root.after(0, self._no_device)
            return
        try:
            self.cam = Camera()
        except Exception as e:
            self.root.after(0, lambda: self._fatal(str(e)))
            return
        self.root.after(0, lambda: (self.photo_btn.config(state="normal"),
                                    self.rec_btn.config(state="normal")))
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self):
        while self.running and self.cam is not None:
            try:
                ok, frame = self.cam.read()
            except Exception:
                continue
            if not ok:
                continue
            if self.rotation in ROTATIONS:
                frame = cv2.rotate(frame, ROTATIONS[self.rotation])
            self.frame = frame
            self.frames += 1
            self._record(frame)

    # ------------------------------------------------------------------- view
    def _tick(self):
        if not self.running:
            return
        frame = self.frame
        if frame is not None:
            # Scale to the current video-area size, preserving the aspect ratio.
            vw, vh = self.view.winfo_width(), self.view.winfo_height()
            h, w = frame.shape[:2]
            if vw > 10 and vh > 10:
                scale = min(vw / w, vh / h)
                frame = cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))),
                                   interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.video.config(image=self.imgtk)
            self._update_status(w, h)
        self.root.after(33, self._tick)  # ~30 Hz UI refresh

    def _update_status(self, w, h):
        now = time.monotonic()
        t, n = self._fps_mark
        if now - t >= 1.0:
            self.fps = (self.frames - n) / (now - t)
            self._fps_mark = (now, self.frames)
        if self.writer is not None:
            secs = int(now - self.rec_start)
            self.status.config(text=f"● REC {secs // 60:02d}:{secs % 60:02d}", fg=RED)
        elif self.message and now < self.message_until:
            self.status.config(text=self.message, fg=FG)
        else:
            self.status.config(text=f"En direct · {w}×{h} · {self.fps:0.1f} FPS", fg=DIM)

    def _flash(self, text, secs=4.0):
        self.message, self.message_until = text, time.monotonic() + secs

    # ---------------------------------------------------------------- actions
    def rotate(self):
        if self.writer is not None:
            self._flash("Rotation impossible pendant l'enregistrement")
            return
        self.rotation = (self.rotation + 90) % 360
        self.settings["rotation"] = self.rotation
        save_settings(self.settings)
        self._flash(f"Rotation {self.rotation}°", 1.5)

    def take_photo(self):
        frame = self.frame
        if frame is None:
            return
        os.makedirs(SAVE_DIR, exist_ok=True)
        name = time.strftime("endoscope-%Y%m%d-%H%M%S.jpg")
        cv2.imwrite(os.path.join(SAVE_DIR, name), frame,
                    [cv2.IMWRITE_JPEG_QUALITY, PHOTO_QUALITY])
        self._flash(f"Photo enregistrée : {name}")

    def toggle_recording(self):
        if self.writer is None:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        frame = self.frame
        if frame is None or self.writer is not None:
            return
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, time.strftime("endoscope-%Y%m%d-%H%M%S.mp4"))
        h, w = frame.shape[:2]
        writer = None
        for codec in ("avc1", "mp4v"):   # H.264 if available, else MPEG-4
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), REC_FPS, (w, h))
            if writer.isOpened():
                break
            writer.release()
            writer = None
        if writer is None:
            messagebox.showerror("ProbeView", "Impossible de créer le fichier vidéo.")
            return
        with self.rec_lock:
            self.rec_path, self.rec_start, self.rec_written = path, time.monotonic(), 0
            self.writer = writer
        self.rec_btn.config(text="■ Arrêter")
        self.rot_btn.config(state="disabled")

    def _record(self, frame):
        """Called from the capture thread. Keeps the file in real time: frames are
        repeated or skipped so the video lasts as long as the recording did."""
        with self.rec_lock:
            if self.writer is None:
                return
            due = int((time.monotonic() - self.rec_start) * REC_FPS) + 1
            for _ in range(min(due - self.rec_written, REC_FPS)):
                self.writer.write(frame)
                self.rec_written += 1
            self.rec_written = max(self.rec_written, due - REC_FPS)

    def stop_recording(self):
        with self.rec_lock:
            writer, self.writer = self.writer, None
            path, secs = self.rec_path, int(time.monotonic() - self.rec_start)
        if writer is None:
            return
        writer.release()
        try:
            self.rec_btn.config(text="● Enregistrer")
            self.rot_btn.config(state="normal")
            self._flash(f"Vidéo enregistrée : {os.path.basename(path)} "
                        f"({secs // 60:02d}:{secs % 60:02d})")
        except tk.TclError:
            pass  # window already gone

    def open_folder(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        subprocess.run(["open", SAVE_DIR])

    # --------------------------------------------------------------- lifecycle
    def _no_device(self):
        self.status.config(text="Aucun endoscope trouvé")
        messagebox.showinfo(
            "ProbeView",
            "Aucun endoscope trouvé.\n\nBranchez l'endoscope USB (avec un câble de "
            "données, pas un câble de charge seule), acceptez la demande macOS "
            "« Autoriser l'accessoire », puis relancez ProbeView.",
        )
        self.on_close()

    def _fatal(self, msg):
        messagebox.showerror("ProbeView", f"Impossible de démarrer la caméra :\n\n{msg}")
        self.on_close()

    def on_close(self):
        self.running = False
        self.stop_recording()
        if self.cam is not None:
            try:
                self.cam.release()
            except Exception:
                pass
            self.cam = None
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = ProbeViewApp(root)
    # macOS Cmd-Q / "Quit ProbeView" bypasses WM_DELETE_WINDOW; release the camera too.
    root.createcommand("::tk::mac::Quit", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
