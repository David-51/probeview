#!/usr/bin/env python3
"""app.py — ProbeView: double-clickable endoscope viewer.

Native (Tkinter) window: live video scaled to the window, rotation, photo, video
recording (MP4), network broadcast (MJPEG + web page, e.g. for OBS) and a built-in
help window. Capture runs on a background thread; the UI is updated on the main
thread via .after().

Photos and videos go to ~/Desktop/ProbeView. The rotation is remembered.

Keys: Space = photo, R = rotate, V = record, D = broadcast, H = help.
"""
import json
import os
import signal
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk

from server import FrameHub, lan_addresses, serve_in_background
from upp_camera import Camera, list_devices

SAVE_DIR = os.path.expanduser("~/Desktop/ProbeView")
SETTINGS = os.path.expanduser("~/Library/Application Support/ProbeView/settings.json")
REC_FPS = 15                 # camera delivers ~15 FPS
PHOTO_QUALITY = 95
STREAM_QUALITY = 85
BROADCAST_PORT = 8080        # first port tried; the next free one is used if busy
REPO_URL = "https://github.com/David-51/probeview"
ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
             270: cv2.ROTATE_90_COUNTERCLOCKWISE}

BG, FG, DIM, RED, LINK = "#1e1e1e", "#cccccc", "#888888", "#ff5555", "#6cb6ff"


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


def help_content(page_url, stream_url):
    """Help text as (style, text) pairs. Styles: h1, h2, p, key (text = (key, desc))."""
    if page_url:
        address = [("p", f"Diffusion en cours.\n  Page web : {page_url}\n"
                         f"  Flux pour OBS / VLC : {stream_url}")]
    else:
        address = [("p", "Diffusion arrêtée : cliquez sur « Diffuser » pour afficher ici "
                         "les adresses à utiliser.")]
    return [
        ("h1", "ProbeView — Aide"),
        ("p", "ProbeView affiche l'image d'un endoscope USB « Useeplus / Geek szitman », "
              "prend des photos, enregistre des vidéos et peut diffuser l'image sur votre "
              "réseau local (téléphone, autre ordinateur, OBS…)."),

        ("h2", "Démarrer"),
        ("p", "1. Branchez l'endoscope avec un câble qui transporte les données (pas un "
              "câble de charge seule).\n"
              "2. Si macOS demande d'« autoriser l'accessoire », acceptez.\n"
              "3. L'image apparaît en quelques secondes. En bas s'affiche "
              "« En direct · 640×480 · 15 FPS »."),

        ("h2", "Boutons et raccourcis clavier"),
        ("key", ("↻ Pivoter   R", "Tourne l'image d'un quart de tour. Le réglage est "
                                  "gardé pour la prochaine fois. Impossible pendant un "
                                  "enregistrement.")),
        ("key", ("Photo   Espace", "Enregistre l'image affichée (avec la rotation) en JPEG.")),
        ("key", ("● Enregistrer   V", "Démarre une vidéo ; « ● REC 00:12 » s'affiche en "
                                      "rouge. Cliquez sur « ■ Arrêter » (ou V) pour la "
                                      "terminer.")),
        ("key", ("Diffuser   D", "Envoie l'image sur le réseau local, voir plus bas. "
                                 "Cliquez sur « ■ Stop diffusion » (ou D) pour arrêter.")),
        ("key", ("Dossier", "Ouvre le dossier des photos et vidéos dans le Finder.")),
        ("key", ("Aide   H", "Ouvre cette fenêtre.")),
        ("key", ("Quitter   ⌘Q", "Ferme ProbeView (la vidéo en cours est enregistrée).")),
        ("p", "La fenêtre peut être agrandie ou mise en plein écran : l'image suit."),

        ("h2", "Photos et vidéos"),
        ("p", "• Elles vont dans le dossier « ProbeView » sur le Bureau, nommées "
              "endoscope-AAAAMMJJ-HHMMSS.jpg ou .mp4.\n"
              "• Les vidéos sont en MP4 (H.264) à 15 images/s : elles s'ouvrent avec "
              "QuickTime, VLC ou un logiciel de montage.\n"
              "• À la première capture, macOS peut demander si ProbeView peut accéder "
              "au Bureau : acceptez.\n"
              "• La caméra fournit du 640×480 : c'est sa résolution réelle, même si "
              "l'emballage annonce davantage."),

        ("h2", "Diffuser sur le réseau"),
        ("p", "Pendant la diffusion, ProbeView continue de fonctionner normalement "
              "(photos, vidéos) et publie en plus l'image sur votre réseau local. Les "
              "adresses s'affichent en bas de la fenêtre : cliquez sur la première pour "
              "ouvrir la page web, et sur « Copier » pour copier l'adresse du flux."),
        *address,
        ("p", "Sur un téléphone, une tablette ou un autre ordinateur connecté au même "
              "Wi-Fi : ouvrez la page web dans le navigateur. Elle a ses propres boutons "
              "Pivoter, Plein écran et Capture."),
        ("p", "Dans OBS Studio :\n"
              "1. Sources → + → Source média.\n"
              "2. Décochez « Fichier local ».\n"
              "3. Dans « Entrée », collez l'adresse du flux (elle se termine par "
              "/stream.mjpg). Sur le même Mac, http://localhost:8080/stream.mjpg marche "
              "aussi.\n"
              "4. Si l'image n'apparaît pas, mettez « mjpeg » dans « Format d'entrée »."),
        ("p", "Dans VLC : Fichier → Ouvrir un flux réseau → collez l'adresse du flux."),
        ("p", "• La première fois, macOS demande « Autoriser ProbeView à rechercher des "
              "appareils sur les réseaux locaux ? » : cliquez sur « Autoriser », sinon les "
              "autres appareils ne recevront pas l'image. Si vous avez refusé : Réglages "
              "Système → Confidentialité et sécurité → Réseau local → activez ProbeView.\n"
              "• Si le coupe-feu de macOS est activé, il peut aussi demander si ProbeView "
              "peut accepter des connexions entrantes : « Autoriser ».\n"
              "• Le port est 8080 ; s'il est déjà pris, ProbeView utilise le suivant "
              "(8081…). L'adresse affichée en bas est toujours la bonne.\n"
              "• Sécurité : il n'y a pas de mot de passe. Toute personne sur le même "
              "réseau qui connaît l'adresse peut voir l'image. Arrêtez la diffusion sur "
              "un réseau public (hôtel, gare…)."),

        ("h2", "En cas de problème"),
        ("key", ("« Aucun endoscope détecté »", "Vérifiez le câble (données, pas charge "
                                                "seule) et branchez la caméra : ProbeView "
                                                "la détecte tout seul, sans relancer.")),
        ("key", ("« Caméra indisponible (déjà utilisée…) »", "Un autre programme utilise "
                                                             "la caméra (par exemple "
                                                             "start-server.command) : "
                                                             "fermez-le, ProbeView se "
                                                             "connecte ensuite tout seul.")),
        ("key", ("Image figée", "Débranchez et rebranchez l'endoscope, puis relancez "
                                "ProbeView.")),
        ("key", ("Diffusion inaccessible", "L'autre appareil doit être sur le même "
                                           "réseau. Vérifiez l'autorisation « Réseau local » "
                                           "(Réglages Système → Confidentialité et sécurité) "
                                           "et le coupe-feu, et utilisez l'adresse "
                                           "affichée en bas : elle peut changer d'un "
                                           "réseau à l'autre.")),
        ("key", ("Double objectif", "Un appui long sur le bouton de la caméra change "
                                    "d'objectif.")),

        ("h2", "À propos"),
        ("p", f"ProbeView est un logiciel libre (licence MIT), non officiel, réalisé avec "
              f"l'aide d'une IA. Code source, mises à jour et documentation :\n{REPO_URL}"),
    ]


class ProbeViewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ProbeView")
        self.root.configure(bg=BG)
        self.root.minsize(640, 460)
        self.root.geometry("900x720")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Two-row bar pinned to the bottom; video fills the rest and scales with it.
        bar = tk.Frame(root, bg=BG)
        bar.pack(side="bottom", fill="x", padx=10, pady=(0, 8))
        buttons = tk.Frame(bar, bg=BG)
        buttons.pack(side="top", fill="x")
        info = tk.Frame(bar, bg=BG)
        info.pack(side="top", fill="x", pady=(6, 0))

        # The video area's size comes from the window, never from the image: a Label
        # that sizes itself to its image would grow a few pixels per refresh.
        self.view = tk.Frame(root, bg="#000000")
        self.view.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 6))
        self.view.pack_propagate(False)
        self.video = tk.Label(self.view, bg="#000000", bd=0, highlightthickness=0)
        self.video.place(relx=0.5, rely=0.5, anchor="center")

        self.rot_btn = tk.Button(buttons, text="↻ Pivoter", command=self.rotate, width=8)
        self.photo_btn = tk.Button(buttons, text="Photo", command=self.take_photo, width=6)
        self.rec_btn = tk.Button(buttons, text="● Enregistrer", command=self.toggle_recording,
                                 width=11)
        self.cast_btn = tk.Button(buttons, text="Diffuser", command=self.toggle_broadcast,
                                  width=12)
        self.dir_btn = tk.Button(buttons, text="Dossier", command=self.open_folder, width=6)
        for b in (self.rot_btn, self.photo_btn, self.rec_btn, self.cast_btn, self.dir_btn):
            b.pack(side="left", padx=(0, 6))
        self.help_btn = tk.Button(buttons, text="? Aide", command=self.show_help, width=6)
        self.help_btn.pack(side="right")
        for b in (self.photo_btn, self.rec_btn, self.cast_btn):
            b.config(state="disabled")

        self.status = tk.Label(info, text="Connexion…", fg=FG, bg=BG, anchor="w")
        self.status.pack(side="left")
        self.copy_btn = tk.Button(info, text="Copier l'adresse OBS", command=self.copy_stream_url)
        self.net_label = tk.Label(info, fg=LINK, bg=BG, cursor="pointinghand")
        self.net_label.bind("<Button-1>", lambda e: self.page_url and subprocess.run(
            ["open", self.page_url]))

        root.bind("<space>", lambda e: self.take_photo())
        root.bind("<Key-r>", lambda e: self.rotate())
        root.bind("<Key-v>", lambda e: self.toggle_recording())
        root.bind("<Key-d>", lambda e: self.toggle_broadcast())
        root.bind("<Key-h>", lambda e: self.show_help())

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

        self.hub = None              # set while broadcasting
        self.server = None
        self.page_url = self.stream_url = None
        self.help_win = None

        # Open the camera on a worker so the window paints immediately.
        self.closing = False
        self.capture_thread = None
        threading.Thread(target=self._open_camera, daemon=True).start()
        self._tick()

    # ----------------------------------------------------------------- camera
    def _open_camera(self):
        """Wait for the endoscope and open it; the window stays usable (help) meanwhile."""
        while self.running:
            if not list_devices():
                self._set_status("Aucun endoscope détecté : branchez-le (voir « ? Aide »)", RED)
                time.sleep(2.0)
                continue
            self._set_status("Connexion à la caméra…", FG)
            try:
                self.cam = Camera()
                break
            except Exception as e:
                reason = ("déjà utilisée par un autre programme" if "Access denied" in str(e)
                          else str(e))
                self._set_status(f"Caméra indisponible ({reason}) : nouvel essai…", RED)
                time.sleep(3.0)
        if not self.running:
            return          # closing: the process exit releases the device
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        self._set_ready()

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
            hub = self.hub
            if hub is not None:
                ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_QUALITY])
                if ok:
                    hub.resolution = (frame.shape[1], frame.shape[0])
                    hub.publish(jpeg.tobytes())

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
            if self.hub is not None:
                self.hub.fps = self.fps
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

    def toggle_broadcast(self):
        if self.hub is None:
            self.start_broadcast()
        else:
            self.stop_broadcast()

    def start_broadcast(self):
        if self.cam is None or self.hub is not None:
            return
        hub = FrameHub()
        hub.connected, hub.mode = True, self.cam.mode
        try:
            server, port = serve_in_background(hub, "0.0.0.0", BROADCAST_PORT)
        except OSError as e:
            messagebox.showerror("ProbeView", f"Impossible de démarrer la diffusion :\n\n{e}")
            return
        self.hub, self.server = hub, server
        host = (lan_addresses() or ["localhost"])[0]
        self.page_url = f"http://{host}:{port}"
        self.stream_url = f"{self.page_url}/stream.mjpg"
        self.cast_btn.config(text="■ Stop diffusion")
        self.copy_btn.pack(side="right")
        self.net_label.config(text=f"📡 {self.page_url}")
        self.net_label.pack(side="right", padx=(0, 8))
        self._flash("Diffusion démarrée")
        self._refresh_help()

    def stop_broadcast(self):
        hub, server = self.hub, self.server
        if hub is None:
            return
        self.hub = self.server = None
        self.page_url = self.stream_url = None
        hub.running = False            # ends open MJPEG streams

        def shutdown():
            server.shutdown()
            server.server_close()
        threading.Thread(target=shutdown, daemon=True).start()
        try:
            self.cast_btn.config(text="Diffuser")
            self.copy_btn.pack_forget()
            self.net_label.pack_forget()
            self._flash("Diffusion arrêtée")
            self._refresh_help()
        except tk.TclError:
            pass  # window already gone

    def copy_stream_url(self):
        if self.stream_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.stream_url)
            self._flash(f"Copié : {self.stream_url}")

    def open_folder(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        subprocess.run(["open", SAVE_DIR])

    # ------------------------------------------------------------------- help
    def show_help(self):
        if self.help_win is not None and self.help_win.winfo_exists():
            self._refresh_help()
            self.help_win.deiconify()
            self.help_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("Aide — ProbeView")
        win.configure(bg=BG)
        win.geometry("640x680")
        win.minsize(420, 320)
        win.bind("<Escape>", lambda e: win.destroy())

        close = tk.Button(win, text="Fermer", command=win.destroy, width=8)
        close.pack(side="bottom", anchor="e", padx=12, pady=10)
        scroll = tk.Scrollbar(win)
        scroll.pack(side="right", fill="y")
        text = tk.Text(win, wrap="word", bg=BG, fg=FG, bd=0, highlightthickness=0,
                       padx=22, pady=16, spacing1=2, spacing3=2, cursor="arrow",
                       yscrollcommand=scroll.set, font=("Helvetica", 13))
        text.pack(side="left", fill="both", expand=True)
        scroll.config(command=text.yview)
        text.tag_configure("h1", font=("Helvetica", 20, "bold"), foreground="#ffffff",
                           spacing3=8)
        text.tag_configure("h2", font=("Helvetica", 15, "bold"), foreground="#ffffff",
                           spacing1=16, spacing3=4)
        text.tag_configure("p", spacing3=8)
        text.tag_configure("key", font=("Helvetica", 13, "bold"), foreground=LINK)
        text.tag_configure("desc", lmargin1=0, lmargin2=0, spacing3=6)
        self.help_win, self.help_text = win, text
        self._refresh_help()

    def _refresh_help(self):
        if self.help_win is None or not self.help_win.winfo_exists():
            return
        text = self.help_text
        top = text.yview()[0]
        text.config(state="normal")
        text.delete("1.0", "end")
        for style, content in help_content(self.page_url, self.stream_url):
            if style == "key":
                key, desc = content
                text.insert("end", key, "key")
                text.insert("end", f" — {desc}\n", "desc")
            else:
                text.insert("end", content + "\n", style)
        text.config(state="disabled")
        text.yview_moveto(top)

    # --------------------------------------------------------------- lifecycle
    def _set_ready(self):
        try:
            self.root.after(0, lambda: [b.config(state="normal")
                                        for b in (self.photo_btn, self.rec_btn, self.cast_btn)])
        except (RuntimeError, tk.TclError):
            pass  # window closed

    def _set_status(self, text, color):
        """Thread-safe status update (used before the first frame arrives)."""
        def apply():
            if self.frame is None:
                self.status.config(text=text, fg=color)
        try:
            self.root.after(0, apply)
        except (RuntimeError, tk.TclError):
            pass  # window closed

    def on_close(self):
        """Stop in order: capture thread, recording, broadcast, then the camera. The
        camera is only released once the capture thread has really stopped: releasing
        it (or letting Python finalize cv2 / libusb) under a running thread crashes."""
        if self.closing:
            return
        self.closing = True
        self.running = False
        try:
            self.root.withdraw()       # disappear at once; cleanup takes a moment
        except tk.TclError:
            pass
        thread = self.capture_thread
        if thread is not None:
            thread.join(timeout=3.0)   # a read returns within ~70 ms while streaming
        self.stop_recording()
        self.stop_broadcast()
        if self.cam is not None and (thread is None or not thread.is_alive()):
            try:
                self.cam.release()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = ProbeViewApp(root)
    # macOS Cmd-Q / "Quit ProbeView" bypasses WM_DELETE_WINDOW; release the camera too.
    root.createcommand("::tk::mac::Quit", app.on_close)
    signal.signal(signal.SIGTERM, lambda *_: root.after(0, app.on_close))
    root.mainloop()
    # Everything is saved and released by now. Exit without interpreter finalization,
    # which tears down cv2/libusb objects under still-running daemon threads.
    os._exit(0)


if __name__ == "__main__":
    main()
