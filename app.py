#!/usr/bin/env python3
"""app.py — ProbeView: double-clickable endoscope viewer.

Minimal native (Tkinter) window: live video, a Save Frame button, and a status
line. Friendly dialog when the device isn't plugged in. Capture runs on a
background thread; the UI is updated on the main thread via .after().

Saved frames go to ~/Desktop/ProbeView.
"""
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk

from upp_camera import Camera, list_devices

SAVE_DIR = os.path.expanduser("~/Desktop/ProbeView")


class ProbeViewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ProbeView Endoscope")
        self.root.configure(bg="#1e1e1e")
        self.root.minsize(480, 400)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Button bar pinned to the bottom; video fills the rest and scales with it.
        bar = tk.Frame(root, bg="#1e1e1e")
        bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        self.video = tk.Label(root, bg="#000000")
        self.video.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 6))
        self.save_btn = tk.Button(bar, text="Save Frame", command=self.save_frame,
                                  width=14, state="disabled")
        self.save_btn.pack(side="left")
        self.status = tk.Label(bar, text="Connecting…", fg="#cccccc", bg="#1e1e1e",
                               anchor="w")
        self.status.pack(side="left", padx=12)

        self.cam = None
        self.latest_jpeg = None
        self.latest_imgtk = None
        self.running = True
        self.frames = 0
        self.t0 = time.monotonic()

        # Open the camera on a worker so the window paints immediately.
        threading.Thread(target=self._open_camera, daemon=True).start()
        self._tick()

    def _open_camera(self):
        if not list_devices():
            self.root.after(0, self._no_device)
            return
        try:
            self.cam = Camera()
        except Exception as e:
            self.root.after(0, lambda: self._fatal(str(e)))
            return
        self.root.after(0, lambda: self.save_btn.config(state="normal"))
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self):
        while self.running and self.cam is not None:
            try:
                jpeg = self.cam.read_jpeg()
            except Exception:
                continue
            if jpeg:
                self.latest_jpeg = jpeg
                self.frames += 1

    def _tick(self):
        if not self.running:
            return
        jpeg = self.latest_jpeg
        if jpeg:
            import numpy as np
            arr = cv2.imdecode(np.frombuffer(jpeg, dtype="uint8"), cv2.IMREAD_COLOR)
            if arr is not None:
                # Scale to the current video-area size, preserving 4:3 (letterboxed).
                vw = max(1, self.video.winfo_width())
                vh = max(1, self.video.winfo_height())
                h, w = arr.shape[:2]
                if vw > 10 and vh > 10:
                    scale = min(vw / w, vh / h)
                    arr = cv2.resize(arr, (max(1, int(w * scale)), max(1, int(h * scale))),
                                     interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
                rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
                self.latest_imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.video.config(image=self.latest_imgtk)
                fps = self.frames / max(1e-6, time.monotonic() - self.t0)
                self.status.config(text=f"Live · 640×480 · {fps:0.1f} FPS")
        self.root.after(33, self._tick)  # ~30 Hz UI refresh

    def save_frame(self):
        if not self.latest_jpeg:
            return
        os.makedirs(SAVE_DIR, exist_ok=True)
        name = time.strftime("endoscope-%Y%m%d-%H%M%S.jpg")
        path = os.path.join(SAVE_DIR, name)
        with open(path, "wb") as f:
            f.write(self.latest_jpeg)
        self.status.config(text=f"Saved {name}")

    def _no_device(self):
        self.status.config(text="No endoscope found")
        messagebox.showinfo(
            "ProbeView",
            "No endoscope found.\n\nPlug in the USB endoscope (use a data cable, not a "
            "charge-only one), approve the macOS “Allow accessory” prompt, then "
            "reopen ProbeView.",
        )
        self.on_close()

    def _fatal(self, msg):
        messagebox.showerror("ProbeView", f"Could not start the camera:\n\n{msg}")
        self.on_close()

    def on_close(self):
        self.running = False
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
    ProbeViewApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
