# ProbeView

**🇫🇷 [Français](#français) · 🇬🇧 [English](#english)**

Voir l'image d'un endoscope USB « Useeplus / Geek szitman » sur un Mac, dans le navigateur, depuis n'importe quel appareil du réseau local.
View a "Useeplus / Geek szitman" USB endoscope on a Mac, in your browser, from any device on your local network.

---

## Français

### À quoi ça sert

Beaucoup d'endoscopes USB bon marché (souvent vendus avec l'appli **Useeplus**) ne fonctionnent officiellement qu'avec un téléphone Android ou un iPhone. Branchés sur un Mac, rien ne se passe : ce ne sont pas des webcams standard et aucune appli n'existe pour macOS.

ProbeView parle directement à la caméra et affiche son image :

- dans une **page web**, consultable sur le Mac ou depuis un téléphone, une tablette ou un autre PC du même réseau Wi-Fi ;
- avec des boutons **Pivoter**, **Plein écran** et **Capture** ;
- la caméra est retrouvée automatiquement si on la débranche et la rebranche.

### Caméras compatibles

Les endoscopes qui apparaissent en USB avec l'identifiant **`2ce3:3828`** (fabricant « Geek szitman », produit « supercamera » ou « useepluscam »). Deux versions de firmware existent sous ce même identifiant et sont toutes les deux prises en charge.

Pour vérifier la vôtre, caméra branchée, dans le Terminal :

```bash
ioreg -p IOUSB | grep -i -E "supercamera|useeplus"
```

Testé sur un endoscope double objectif vendu sous l'appli Useeplus (firmware i4season su4p-002), sur un Mac Apple Silicon.

### Ce qu'il faut

- Un **Mac** (testé sur Apple Silicon, macOS récent).
- [**Homebrew**](https://brew.sh), puis **libusb** et **Python 3** :
  ```bash
  brew install libusb python
  ```
- Un câble USB **qui transporte les données** (pas un câble de charge seule) ou l'adaptateur fourni.

### Installation

```bash
git clone https://github.com/David-51/probeview.git
cd probeview
```

C'est tout : le premier lancement installe le reste tout seul.

### Utilisation

1. Branchez l'endoscope. Si macOS demande d'**autoriser l'accessoire**, acceptez.
2. Dans le Finder, **double-cliquez sur `start-server.command`**.
   (Ou dans le Terminal : `./start-server.command`)
3. Le navigateur s'ouvre sur l'image. Le Terminal affiche aussi une adresse du type :
   ```
   LAN      : http://192.168.1.42:8080
   ```
   Tapez-la dans le navigateur d'un téléphone ou d'un autre ordinateur **connecté au même réseau** pour voir l'image dessus.
4. Pour arrêter : **Ctrl-C** dans le Terminal, ou fermez la fenêtre.

> La première fois, macOS peut demander si Python peut **accepter des connexions entrantes** : répondez *Autoriser* pour pouvoir regarder depuis un autre appareil.

Si macOS bloque le double-clic sur `start-server.command` (« impossible de vérifier le développeur »), faites clic droit → **Ouvrir**, ou lancez-le une fois depuis le Terminal.

**Options**

| Commande | Effet |
|---|---|
| `PORT=9000 ./start-server.command` | utiliser un autre port |
| `NO_BROWSER=1 ./start-server.command` | ne pas ouvrir le navigateur |
| `./start-server.command --host 127.0.0.1` | visible uniquement sur ce Mac |

**Adresses utiles** (remplacez par l'adresse de votre Mac)

- `http://…:8080/` — la page de visionnage
- `http://…:8080/stream.mjpg` — le flux vidéo seul (s'ouvre aussi dans **VLC** : *Fichier → Ouvrir un flux réseau*)
- `http://…:8080/snapshot.jpg` — la dernière image

### Autres outils (facultatifs)

| Script | Usage |
|---|---|
| `python grab.py` | enregistre une image dans `frame-0001.jpg` |
| `python view.py` | aperçu dans une fenêtre simple (touche `q` pour quitter) |
| `python app.py` | petite appli de bureau avec un bouton « Save Frame » (enregistre dans `~/Desktop/ProbeView`) — nécessite Tkinter : `brew install python-tk@$(.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')` |
| `python vcam.py` | expose la caméra comme webcam virtuelle via OBS — nécessite OBS Studio et `pip install pyvirtualcam` |

Lancez-les après avoir activé l'environnement : `source .venv/bin/activate`.

Pour fabriquer une appli `ProbeView.app` à double-cliquer (à partir de `app.py`) :

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --windowed --noconfirm --clean --name ProbeView \
  --add-binary "$(readlink -f /opt/homebrew/lib/libusb-1.0.dylib):." app.py
# résultat : dist/ProbeView.app
```

### Bon à savoir

- **Résolution réelle : 640×480.** Les pages de vente annoncent souvent « HD 1920×1440 / 2 Mpx ». Les applis officielles enregistrent bien des fichiers de cette taille, mais il s'agit d'un simple agrandissement : la caméra n'envoie que du 640×480, et les captures de l'appli ne contiennent pas plus de détails. ProbeView affiche donc la même qualité que l'appli officielle.
- **Double objectif** : d'après le fabricant, un appui long sur le bouton de la caméra change d'objectif. Ça se passe dans la caméra, rien à faire côté ProbeView.
- **Sécurité** : la page n'a pas de mot de passe. Toute personne sur votre réseau local qui connaît l'adresse peut voir l'image. Sur un réseau public, utilisez `--host 127.0.0.1`.

### Dépannage

| Problème | Solution |
|---|---|
| « Caméra non connectée » | Vérifiez le câble (données, pas charge seule), débranchez/rebranchez, acceptez la demande « autoriser l'accessoire ». |
| La caméra ne répond plus / image figée | Débranchez et rebranchez l'endoscope. |
| « libusb introuvable » | `brew install libusb` |
| « le port 8080 est déjà utilisé » | `PORT=9000 ./start-server.command` |
| Impossible d'ouvrir la page depuis le téléphone | Même réseau Wi-Fi ? Connexions entrantes autorisées pour Python (Réglages Système → Réseau → Coupe-feu) ? |
| L'image est de travers | Bouton **Pivoter** (le réglage est mémorisé). |

---

## English

### What it does

Many cheap USB endoscopes (often sold with the **Useeplus** app) officially work only with Android phones or iPhones. Plug one into a Mac and nothing happens: they are not standard webcams and there is no macOS app.

ProbeView talks to the camera directly and shows its picture:

- in a **web page**, on the Mac itself or from a phone, tablet or another computer on the same Wi-Fi;
- with **Rotate**, **Fullscreen** and **Snapshot** buttons (the page UI is in French);
- the camera is picked up again automatically if you unplug and replug it.

### Supported cameras

Endoscopes that show up on USB as **`2ce3:3828`** (manufacturer "Geek szitman", product "supercamera" or "useepluscam"). Two firmware variants exist under this ID; both are supported.

To check yours, with the camera plugged in:

```bash
ioreg -p IOUSB | grep -i -E "supercamera|useeplus"
```

Tested with a dual-lens endoscope sold for the Useeplus app (i4season su4p-002 firmware) on an Apple Silicon Mac.

### Requirements

- A **Mac** (tested on Apple Silicon, recent macOS).
- [**Homebrew**](https://brew.sh), then **libusb** and **Python 3**:
  ```bash
  brew install libusb python
  ```
- A USB cable that **carries data** (not charge-only), or the adapter shipped with the camera.

### Install

```bash
git clone https://github.com/David-51/probeview.git
cd probeview
```

That's it: the first launch installs everything else.

### Usage

1. Plug in the endoscope. If macOS asks to **allow the accessory**, accept.
2. In Finder, **double-click `start-server.command`**.
   (Or in Terminal: `./start-server.command`)
3. Your browser opens on the live picture. Terminal also prints an address like:
   ```
   LAN      : http://192.168.1.42:8080
   ```
   Open it in the browser of a phone or another computer **on the same network**.
4. To stop: **Ctrl-C** in Terminal, or close the window.

> The first time, macOS may ask whether Python may **accept incoming connections**: choose *Allow* to watch from another device.

If macOS refuses to open `start-server.command` ("unidentified developer"), right-click → **Open**, or run it once from Terminal.

**Options**

| Command | Effect |
|---|---|
| `PORT=9000 ./start-server.command` | use another port |
| `NO_BROWSER=1 ./start-server.command` | don't open the browser |
| `./start-server.command --host 127.0.0.1` | only reachable from this Mac |

**Useful URLs** (replace with your Mac's address)

- `http://…:8080/` — the viewer page
- `http://…:8080/stream.mjpg` — the raw video stream (also opens in **VLC**: *File → Open Network*)
- `http://…:8080/snapshot.jpg` — the latest frame

### Other tools (optional)

| Script | Purpose |
|---|---|
| `python grab.py` | saves one frame to `frame-0001.jpg` |
| `python view.py` | simple preview window (`q` to quit) |
| `python app.py` | small desktop app with a "Save Frame" button (saves to `~/Desktop/ProbeView`) — needs Tkinter: `brew install python-tk@$(.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')` |
| `python vcam.py` | exposes the camera as a virtual webcam through OBS — needs OBS Studio and `pip install pyvirtualcam` |

Run them after activating the environment: `source .venv/bin/activate`.

To build a double-clickable `ProbeView.app` (from `app.py`):

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --windowed --noconfirm --clean --name ProbeView \
  --add-binary "$(readlink -f /opt/homebrew/lib/libusb-1.0.dylib):." app.py
# output: dist/ProbeView.app
```

### Good to know

- **Real resolution: 640×480.** Listings often claim "HD 1920×1440 / 2 MP". The official apps do save files that size, but they are just upscaled: the camera only sends 640×480 and the app's captures hold no extra detail. ProbeView shows the same quality as the official app.
- **Dual lens**: according to the manufacturer, a long press on the camera button switches lenses. It happens inside the camera; nothing to do in ProbeView.
- **Security**: the page has no password. Anyone on your local network who knows the address can see the picture. On a public network, use `--host 127.0.0.1`.

### Troubleshooting

| Problem | Fix |
|---|---|
| "Caméra non connectée" (camera not connected) | Check the cable (data, not charge-only), unplug/replug, accept the "allow accessory" prompt. |
| Camera stops responding / frozen picture | Unplug and replug the endoscope. |
| "libusb introuvable" (libusb not found) | `brew install libusb` |
| "port 8080 déjà utilisé" (port in use) | `PORT=9000 ./start-server.command` |
| Page won't open from the phone | Same Wi-Fi? Incoming connections allowed for Python (System Settings → Network → Firewall)? |
| Picture is sideways | **Pivoter** (rotate) button; the setting is remembered. |

---

## Technical details · Détails techniques

How the USB protocol works (both firmware variants): [docs/PROTOCOL.md](docs/PROTOCOL.md).
Driver: [`upp_camera.py`](upp_camera.py) · web server: [`server.py`](server.py).

## Credits · Remerciements

- [**echase/ProbeView**](https://github.com/echase/ProbeView) by Everitt Chase — the original project this repository builds on.
- [**technicallyvu/usb-scope**](https://github.com/technicallyvu/usb-scope) — documentation of the i4season (YUV) firmware variant.
- [**hbens/geek-szitman-supercamera**](https://github.com/hbens/geek-szitman-supercamera) — the JPEG protocol proof of concept.
- [**Tibiaworx/usee-plus-camera**](https://github.com/Tibiaworx/usee-plus-camera), [**MAkcanca/useeplus-linux-driver**](https://github.com/MAkcanca/useeplus-linux-driver), [**jmz3/EndoscopeCamera**](https://github.com/jmz3/EndoscopeCamera) — protocol research.

## Made with AI · Réalisé avec l'IA

🇫🇷 Ce projet a été développé avec l'aide d'une IA (Claude, d'Anthropic) : diagnostic USB, code et documentation. Il a été testé sur du vrai matériel, mais relisez le code avant de l'utiliser dans un contexte important.

🇬🇧 This project was built with the help of AI (Anthropic's Claude): USB debugging, code and documentation. It was tested on real hardware, but review the code before relying on it for anything important.

## Disclaimer · Avertissement

Unofficial. Not affiliated with or endorsed by the manufacturer or any trademark holder. "Geek szitman", "supercamera", "Useeplus" and "i4season" are mentioned for interoperability only. Provided as-is, for personal and educational use.

Projet non officiel, sans lien avec le fabricant. Les marques citées le sont uniquement à des fins d'interopérabilité. Fourni tel quel.

## License · Licence

[MIT](LICENSE)
