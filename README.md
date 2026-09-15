# ProbeView

**🇫🇷 [Français](#français) · 🇬🇧 [English](#english)**

Utiliser un endoscope USB « Useeplus / Geek szitman » sur un Mac : application avec photos et vidéos, ou image dans le navigateur depuis n'importe quel appareil du réseau local.
Use a "Useeplus / Geek szitman" USB endoscope on a Mac: an app with photos and video, or the live picture in a browser on any device on your local network.

---

## Français

### À quoi ça sert

Beaucoup d'endoscopes USB bon marché (souvent vendus avec l'appli **Useeplus**) ne fonctionnent officiellement qu'avec un téléphone Android ou un iPhone. Branchés sur un Mac, rien ne se passe : ce ne sont pas des webcams standard et aucune appli n'existe pour macOS.

ProbeView parle directement à la caméra. Deux façons de l'utiliser :

- l'**application ProbeView** : image en direct, rotation, **photos** et **enregistrement vidéo** ;
- une **page web**, consultable sur le Mac ou depuis un téléphone, une tablette ou un autre ordinateur du même réseau Wi-Fi.

### Caméras compatibles

Les endoscopes qui apparaissent en USB avec l'identifiant **`2ce3:3828`** (fabricant « Geek szitman », produit « supercamera » ou « useepluscam »). Deux versions de firmware existent sous ce même identifiant et sont toutes les deux prises en charge.

Testé sur un endoscope double objectif vendu avec l'appli Useeplus (firmware i4season su4p-002), sur un Mac Apple Silicon.

Pour vérifier la vôtre, caméra branchée, dans le Terminal : `ioreg -p IOUSB | grep -i -E "supercamera|useeplus"` (une ligne doit s'afficher).

### Installation

Il faut un **Mac**, une **connexion Internet** et environ **10 minutes** la première fois. Le script d'installation s'occupe de tout : outils nécessaires ([Homebrew](https://brew.sh), libusb, Python), fabrication de l'application et copie dans **Applications**.

1. **Téléchargez ProbeView** : en haut de cette page GitHub, bouton vert **Code** → **Download ZIP**. Ouvrez le fichier téléchargé : un dossier **`probeview-main`** apparaît dans *Téléchargements*.
2. **Ouvrez le Terminal** : touches `⌘ Espace`, tapez `Terminal`, touche `Entrée`.
3. **Copiez-collez cette ligne** dans le Terminal, puis `Entrée` :
   ```bash
   bash ~/Downloads/probeview-main/install.command
   ```
   > Le dossier est ailleurs ? Tapez `bash ` (avec un espace), **glissez le fichier `install.command`** depuis le Finder dans la fenêtre du Terminal, puis `Entrée`.

Suivez les messages. Si Homebrew n'est pas encore installé, le script propose de l'installer (répondez `o`) et demande le **mot de passe de votre session Mac** (rien ne s'affiche pendant la saisie, c'est normal).

À la fin, **ProbeView s'ouvre** et se trouve dans **Applications**. Vous pouvez supprimer le fichier ZIP ; gardez le dossier `probeview-main` si vous voulez utiliser la page web.

<details>
<summary>Avec git (si vous connaissez)</summary>

```bash
git clone https://github.com/David-51/probeview.git
cd probeview
./install.command
```
</details>

### Utiliser l'application

1. Branchez l'endoscope. Si macOS demande d'**autoriser l'accessoire**, acceptez.
2. Ouvrez **ProbeView** (Launchpad, Spotlight, ou glissez-la dans le Dock depuis Applications).

| Bouton | Raccourci | Effet |
|---|---|---|
| **↻ Pivoter** | `R` | tourne l'image d'un quart de tour (réglage mémorisé) |
| **Photo** | `Espace` | enregistre l'image affichée en JPEG |
| **● Enregistrer** / **■ Arrêter** | `V` | enregistre une vidéo MP4 (lisible par QuickTime) |
| **Dossier** | | ouvre le dossier des photos et vidéos |

Photos et vidéos vont dans le dossier **ProbeView sur le Bureau** (`~/Desktop/ProbeView`), avec la rotation choisie. La rotation est bloquée pendant un enregistrement. À la première capture, macOS peut demander si ProbeView peut accéder au Bureau : acceptez.

### Voir l'image depuis un autre appareil (page web)

1. Branchez l'endoscope et **fermez l'application ProbeView** (la caméra ne peut servir qu'à un seul programme à la fois).
2. Dans le Terminal :
   ```bash
   bash ~/Downloads/probeview-main/start-server.command
   ```
   (ou `bash ` + glisser le fichier `start-server.command` + `Entrée`)
3. Le navigateur s'ouvre sur l'image. Le Terminal affiche aussi une adresse du type :
   ```
   LAN      : http://192.168.1.42:8080
   ```
   Tapez-la dans le navigateur d'un téléphone ou d'un autre ordinateur **connecté au même réseau**.
4. Pour arrêter : `Ctrl-C` dans le Terminal, ou fermez la fenêtre.

La page propose **Pivoter**, **Plein écran** et **Capture**, et retrouve la caméra si on la débranche et la rebranche. La première fois, macOS peut demander si Python peut **accepter des connexions entrantes** : répondez *Autoriser* pour regarder depuis un autre appareil.

<details>
<summary>Options et adresses utiles</summary>

| Commande | Effet |
|---|---|
| `PORT=9000 bash start-server.command` | utiliser un autre port |
| `NO_BROWSER=1 bash start-server.command` | ne pas ouvrir le navigateur |
| `bash start-server.command --host 127.0.0.1` | visible uniquement sur ce Mac |

- `http://…:8080/` — la page de visionnage
- `http://…:8080/stream.mjpg` — le flux vidéo seul (s'ouvre aussi dans **VLC** : *Fichier → Ouvrir un flux réseau*)
- `http://…:8080/snapshot.jpg` — la dernière image
</details>

### Mettre à jour / désinstaller

- **Mettre à jour** : téléchargez à nouveau le ZIP (ou `git pull`), puis relancez `install.command`. L'application est remplacée.
- **Désinstaller** : mettez **ProbeView** (dans Applications) et le dossier `probeview-main` à la corbeille. Réglage de rotation : `~/Library/Application Support/ProbeView`. Les outils Homebrew restent installés ; ils ne gênent pas.

### Bon à savoir

- **Résolution réelle : 640×480.** Les pages de vente annoncent souvent « HD 1920×1440 / 2 Mpx ». Les applis officielles enregistrent bien des fichiers de cette taille, mais c'est un simple agrandissement : la caméra n'envoie que du 640×480 et les captures de l'appli ne contiennent pas plus de détails. ProbeView offre donc la même qualité que l'appli officielle.
- **Double objectif** : d'après le fabricant, un appui long sur le bouton de la caméra change d'objectif. Ça se passe dans la caméra, rien à faire côté ProbeView.
- **Sécurité** : la page web n'a pas de mot de passe. Toute personne sur votre réseau local qui connaît l'adresse peut voir l'image. Sur un réseau public, utilisez `--host 127.0.0.1`.

### Dépannage

| Problème | Solution |
|---|---|
| Double-clic sur un fichier `.command` refusé (« impossible de vérifier le développeur ») | Normal pour un fichier téléchargé : lancez-le depuis le Terminal avec `bash ` devant, comme indiqué plus haut. |
| `No such file or directory` à l'installation | Le dossier n'est pas dans Téléchargements ou porte un autre nom : utilisez l'astuce « `bash ` + glisser le fichier ». |
| L'installation échoue | Relancez-la (elle reprend là où elle en était) ; vérifiez la connexion Internet. |
| Appli : « Aucun endoscope trouvé » | Vérifiez le câble (données, pas charge seule), branchez la caméra **avant** d'ouvrir l'appli, acceptez « autoriser l'accessoire ». |
| Appli : « Impossible de démarrer la caméra … Access denied » | La caméra est déjà utilisée, souvent par la page web : arrêtez-la (`Ctrl-C` dans le Terminal), puis relancez l'appli. |
| La caméra ne répond plus / image figée | Débranchez et rebranchez l'endoscope. |
| Je ne trouve pas mes photos / vidéos | Bouton **Dossier**, ou dossier *ProbeView* sur le Bureau. |
| L'image est de travers | Bouton **Pivoter** ou touche `R`. |
| Page web : « Caméra non connectée » | Câble, rebranchement, et application ProbeView fermée. |
| Page web : « le port 8080 est déjà utilisé » | `PORT=9000 bash start-server.command` |
| Page web inaccessible depuis le téléphone | Même réseau Wi-Fi ? Connexions entrantes autorisées pour Python (Réglages Système → Réseau → Coupe-feu) ? |

---

## English

### What it does

Many cheap USB endoscopes (often sold with the **Useeplus** app) officially work only with Android phones or iPhones. Plug one into a Mac and nothing happens: they are not standard webcams and there is no macOS app.

ProbeView talks to the camera directly. Two ways to use it:

- the **ProbeView app**: live picture, rotation, **photos** and **video recording**;
- a **web page**, on the Mac itself or from a phone, tablet or another computer on the same Wi-Fi.

Both interfaces are in French (buttons are translated below).

### Supported cameras

Endoscopes that show up on USB as **`2ce3:3828`** (manufacturer "Geek szitman", product "supercamera" or "useepluscam"). Two firmware variants exist under this ID; both are supported.

Tested with a dual-lens endoscope sold for the Useeplus app (i4season su4p-002 firmware) on an Apple Silicon Mac.

To check yours, with the camera plugged in, in Terminal: `ioreg -p IOUSB | grep -i -E "supercamera|useeplus"` (one line should appear).

### Install

You need a **Mac**, an **Internet connection** and about **10 minutes** the first time. The install script handles everything: required tools ([Homebrew](https://brew.sh), libusb, Python), building the app and copying it to **Applications**.

1. **Download ProbeView**: at the top of this GitHub page, green **Code** button → **Download ZIP**. Open the downloaded file: a **`probeview-main`** folder appears in *Downloads*.
2. **Open Terminal**: press `⌘ Space`, type `Terminal`, press `Return`.
3. **Paste this line** into Terminal, then `Return`:
   ```bash
   bash ~/Downloads/probeview-main/install.command
   ```
   > Folder somewhere else? Type `bash ` (with a space), **drag the `install.command` file** from Finder into the Terminal window, then `Return`.

Follow the messages. If Homebrew isn't installed yet, the script offers to install it (answer `y`) and asks for your **Mac login password** (nothing shows while typing; that's normal).

When it's done, **ProbeView opens** and is in **Applications**. You can delete the ZIP; keep the `probeview-main` folder if you want to use the web page.

<details>
<summary>With git (if you know it)</summary>

```bash
git clone https://github.com/David-51/probeview.git
cd probeview
./install.command
```
</details>

### Using the app

1. Plug in the endoscope. If macOS asks to **allow the accessory**, accept.
2. Open **ProbeView** (Launchpad, Spotlight, or drag it to the Dock from Applications).

| Button | Key | Action |
|---|---|---|
| **↻ Pivoter** (rotate) | `R` | rotates the picture a quarter turn (remembered) |
| **Photo** | `Space` | saves the displayed picture as JPEG |
| **● Enregistrer** / **■ Arrêter** (record / stop) | `V` | records an MP4 video (plays in QuickTime) |
| **Dossier** (folder) | | opens the photos and videos folder |

Photos and videos go to the **ProbeView folder on your Desktop** (`~/Desktop/ProbeView`), with the chosen rotation. Rotation is locked while recording. On the first capture, macOS may ask whether ProbeView can access your Desktop: allow it.

### Watching from another device (web page)

1. Plug in the endoscope and **quit the ProbeView app** (only one program can use the camera at a time).
2. In Terminal:
   ```bash
   bash ~/Downloads/probeview-main/start-server.command
   ```
   (or `bash ` + drag the `start-server.command` file + `Return`)
3. Your browser opens on the live picture. Terminal also prints an address like:
   ```
   LAN      : http://192.168.1.42:8080
   ```
   Open it in the browser of a phone or another computer **on the same network**.
4. To stop: `Ctrl-C` in Terminal, or close the window.

The page has **Pivoter** (rotate), **Plein écran** (fullscreen) and **Capture** (snapshot) buttons, and picks the camera up again after unplugging. The first time, macOS may ask whether Python may **accept incoming connections**: choose *Allow* to watch from another device.

<details>
<summary>Options and useful URLs</summary>

| Command | Effect |
|---|---|
| `PORT=9000 bash start-server.command` | use another port |
| `NO_BROWSER=1 bash start-server.command` | don't open the browser |
| `bash start-server.command --host 127.0.0.1` | only reachable from this Mac |

- `http://…:8080/` — the viewer page
- `http://…:8080/stream.mjpg` — the raw video stream (also opens in **VLC**: *File → Open Network*)
- `http://…:8080/snapshot.jpg` — the latest frame
</details>

### Update / uninstall

- **Update**: download the ZIP again (or `git pull`), then run `install.command` again. The app is replaced.
- **Uninstall**: move **ProbeView** (in Applications) and the `probeview-main` folder to the Trash. Rotation setting: `~/Library/Application Support/ProbeView`. Homebrew tools stay installed; they do no harm.

### Good to know

- **Real resolution: 640×480.** Listings often claim "HD 1920×1440 / 2 MP". The official apps do save files that size, but they are just upscaled: the camera only sends 640×480 and the app's captures hold no extra detail. ProbeView gives the same quality as the official app.
- **Dual lens**: according to the manufacturer, a long press on the camera button switches lenses. It happens inside the camera; nothing to do in ProbeView.
- **Security**: the web page has no password. Anyone on your local network who knows the address can see the picture. On a public network, use `--host 127.0.0.1`.

### Troubleshooting

| Problem | Fix |
|---|---|
| Double-clicking a `.command` file is refused ("unidentified developer") | Normal for a downloaded file: run it from Terminal with `bash ` in front, as shown above. |
| `No such file or directory` when installing | The folder isn't in Downloads or has another name: use the "`bash ` + drag the file" trick. |
| Install fails | Run it again (it picks up where it stopped); check your Internet connection. |
| App: "Aucun endoscope trouvé" (no endoscope found) | Check the cable (data, not charge-only), plug the camera in **before** opening the app, accept "allow accessory". |
| App: "Impossible de démarrer la caméra … Access denied" (can't start camera) | The camera is already in use, usually by the web page: stop it (`Ctrl-C` in Terminal), then reopen the app. |
| Camera stops responding / frozen picture | Unplug and replug the endoscope. |
| Can't find photos / videos | **Dossier** (folder) button, or the *ProbeView* folder on your Desktop. |
| Picture is sideways | **Pivoter** (rotate) button or `R` key. |
| Web page: "Caméra non connectée" (camera not connected) | Cable, replug, and make sure the ProbeView app is closed. |
| Web page: "port 8080 déjà utilisé" (port in use) | `PORT=9000 bash start-server.command` |
| Web page won't open from the phone | Same Wi-Fi? Incoming connections allowed for Python (System Settings → Network → Firewall)? |

---

## For developers · Pour les développeurs

- USB protocol (both firmware variants): [docs/PROTOCOL.md](docs/PROTOCOL.md)
- Driver: [`upp_camera.py`](upp_camera.py) · app: [`app.py`](app.py) · web server: [`server.py`](server.py) · installer: [`install.command`](install.command)
- After `install.command`, the Python environment is in `.venv`. Other scripts: `grab.py` (save one frame), `view.py` (OpenCV preview window, `q` to quit), `vcam.py` (virtual webcam through OBS, needs `pip install pyvirtualcam`). Run `source .venv/bin/activate` first.
- Manual app build: `.venv/bin/pyinstaller --windowed --noconfirm --clean --name ProbeView --add-binary "$(readlink -f "$(brew --prefix libusb)/lib/libusb-1.0.dylib"):." app.py`

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
