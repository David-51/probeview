# ProbeView

**🇫🇷 [Français](#français) · 🇬🇧 [English](#english)**

Utiliser un endoscope USB « Useeplus / Geek szitman » sur un Mac : application avec photos, vidéos et diffusion sur le réseau local (téléphone, OBS…).
Use a "Useeplus / Geek szitman" USB endoscope on a Mac: an app with photos, video and local network broadcast (phone, OBS…).

---

## Français

### À quoi ça sert

Beaucoup d'endoscopes USB bon marché (souvent vendus avec l'appli **Useeplus**) ne fonctionnent officiellement qu'avec un téléphone Android ou un iPhone. Branchés sur un Mac, rien ne se passe : ce ne sont pas des webcams standard et aucune appli n'existe pour macOS.

ProbeView parle directement à la caméra. Deux façons de l'utiliser :

- l'**application ProbeView** : image en direct, rotation, **photos**, **enregistrement vidéo** et **diffusion sur le réseau local** (téléphone, autre ordinateur, **OBS**, VLC), avec une aide intégrée ;
- un **serveur seul**, sans application, pour regarder dans un navigateur.

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

À la fin, **ProbeView s'ouvre** et se trouve dans **Applications**. Vous pouvez supprimer le fichier ZIP ; gardez le dossier `probeview-main` si vous voulez utiliser le serveur seul.

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
2. Ouvrez **ProbeView** (Launchpad, Spotlight, ou glissez-la dans le Dock depuis Applications). Si la caméra n'est pas encore branchée, l'appli l'attend et se connecte dès qu'elle est détectée.

| Bouton | Raccourci | Effet |
|---|---|---|
| **↻ Pivoter** | `R` | tourne l'image d'un quart de tour (réglage mémorisé) |
| **Photo** | `Espace` | enregistre l'image affichée en JPEG |
| **● Enregistrer** / **■ Arrêter** | `V` | enregistre une vidéo MP4 (lisible par QuickTime) |
| **Diffuser** / **■ Stop diffusion** | `D` | envoie l'image sur le réseau local (voir ci-dessous) |
| **Dossier** | | ouvre le dossier des photos et vidéos |
| **? Aide** | `H` | mode d'emploi complet, dans l'appli |

Photos et vidéos vont dans le dossier **ProbeView sur le Bureau** (`~/Desktop/ProbeView`), avec la rotation choisie. La rotation est bloquée pendant un enregistrement. À la première capture, macOS peut demander si ProbeView peut accéder au Bureau : acceptez.

### Voir l'image sur un autre appareil ou dans OBS

Cliquez sur **Diffuser** dans l'application. Elle continue de fonctionner normalement (photos, vidéos) et publie en plus l'image sur votre réseau local. En bas de la fenêtre s'affichent :

- l'**adresse de la page web** (par exemple `http://192.168.1.42:8080`) : cliquez dessus, ou tapez-la dans le navigateur d'un téléphone ou d'un ordinateur **connecté au même réseau** ;
- le bouton **Copier l'adresse OBS**, qui copie l'adresse du flux vidéo (`…/stream.mjpg`).

> **La première fois**, macOS demande « Autoriser ProbeView à rechercher des appareils sur les réseaux locaux ? » : cliquez sur **Autoriser**, sinon les autres appareils ne recevront rien. En cas de refus : Réglages Système → Confidentialité et sécurité → **Réseau local** → activez ProbeView.

**Dans OBS Studio** : Sources → **+** → **Source média** → décochez *Fichier local* → dans *Entrée*, collez l'adresse copiée → si l'image n'apparaît pas, mettez `mjpeg` dans *Format d'entrée*.
**Dans VLC** : *Fichier → Ouvrir un flux réseau* → collez l'adresse.

Le port est `8080` ; s'il est déjà pris, ProbeView utilise le suivant (`8081`…) : l'adresse affichée est toujours la bonne. La page web a ses propres boutons **Pivoter**, **Plein écran** et **Capture**.

<details>
<summary>Sans l'application : serveur seul (start-server.command)</summary>

Pratique sur un Mac sans écran ou pour un usage permanent. Fermez d'abord l'application ProbeView (la caméra ne peut servir qu'à un seul programme à la fois), puis dans le Terminal :

```bash
bash ~/Downloads/probeview-main/start-server.command
```

Le navigateur s'ouvre et le Terminal affiche l'adresse réseau. `Ctrl-C` pour arrêter. La page retrouve la caméra si on la débranche et la rebranche.

| Commande | Effet |
|---|---|
| `PORT=9000 bash start-server.command` | utiliser un autre port |
| `NO_BROWSER=1 bash start-server.command` | ne pas ouvrir le navigateur |
| `bash start-server.command --host 127.0.0.1` | visible uniquement sur ce Mac |

Adresses : `/` page de visionnage · `/stream.mjpg` flux vidéo · `/snapshot.jpg` dernière image.
</details>

### Mettre à jour / désinstaller

- **Mettre à jour** : téléchargez à nouveau le ZIP (ou `git pull`), puis relancez `install.command`. L'application est remplacée.
- **Désinstaller** : mettez **ProbeView** (dans Applications) et le dossier `probeview-main` à la corbeille. Réglage de rotation : `~/Library/Application Support/ProbeView`. Les outils Homebrew restent installés ; ils ne gênent pas.

### Bon à savoir

- **Résolution réelle : 640×480.** Les pages de vente annoncent souvent « HD 1920×1440 / 2 Mpx ». Les applis officielles enregistrent bien des fichiers de cette taille, mais c'est un simple agrandissement : la caméra n'envoie que du 640×480 et les captures de l'appli ne contiennent pas plus de détails. ProbeView offre donc la même qualité que l'appli officielle.
- **Double objectif** : d'après le fabricant, un appui long sur le bouton de la caméra change d'objectif. Ça se passe dans la caméra, rien à faire côté ProbeView.
- **Sécurité** : la diffusion n'a pas de mot de passe. Toute personne sur votre réseau local qui connaît l'adresse peut voir l'image. Sur un réseau public (hôtel, gare…), n'activez pas **Diffuser** (en serveur seul : `--host 127.0.0.1`).

### Dépannage

| Problème | Solution |
|---|---|
| Double-clic sur un fichier `.command` refusé (« impossible de vérifier le développeur ») | Normal pour un fichier téléchargé : lancez-le depuis le Terminal avec `bash ` devant, comme indiqué plus haut. |
| `No such file or directory` à l'installation | Le dossier n'est pas dans Téléchargements ou porte un autre nom : utilisez l'astuce « `bash ` + glisser le fichier ». |
| L'installation échoue | Relancez-la (elle reprend là où elle en était) ; vérifiez la connexion Internet. |
| Appli : « Aucun endoscope détecté » | Vérifiez le câble (données, pas charge seule) et acceptez « autoriser l'accessoire » : l'appli se connecte dès que la caméra est détectée. |
| Appli : « Caméra indisponible (déjà utilisée par un autre programme) » | Arrêtez `start-server.command` (`Ctrl-C` dans le Terminal) : l'appli se connecte ensuite toute seule. |
| Diffusion : rien sur le téléphone ou dans OBS | Même réseau ? Autorisation **Réseau local** accordée (Réglages Système → Confidentialité et sécurité → Réseau local) ? Adresse bien celle affichée en bas de l'appli ? |
| La caméra ne répond plus / image figée | Débranchez et rebranchez l'endoscope. |
| Je ne trouve pas mes photos / vidéos | Bouton **Dossier**, ou dossier *ProbeView* sur le Bureau. |
| L'image est de travers | Bouton **Pivoter** ou touche `R`. |
| Serveur seul : « Caméra non connectée » | Câble, rebranchement, et application ProbeView fermée. |
| Serveur seul : « le port 8080 est déjà utilisé » | `PORT=9000 bash start-server.command` |
| Serveur seul : page inaccessible depuis le téléphone | Même réseau Wi-Fi ? Connexions entrantes autorisées pour Python (Réglages Système → Réseau → Coupe-feu) ? |

---

## English

### What it does

Many cheap USB endoscopes (often sold with the **Useeplus** app) officially work only with Android phones or iPhones. Plug one into a Mac and nothing happens: they are not standard webcams and there is no macOS app.

ProbeView talks to the camera directly. Two ways to use it:

- the **ProbeView app**: live picture, rotation, **photos**, **video recording** and **local network broadcast** (phone, another computer, **OBS**, VLC), with built-in help;
- a **server only**, without the app, to watch in a browser.

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

When it's done, **ProbeView opens** and is in **Applications**. You can delete the ZIP; keep the `probeview-main` folder if you want to use the server-only mode.

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
2. Open **ProbeView** (Launchpad, Spotlight, or drag it to the Dock from Applications). If the camera isn't plugged in yet, the app waits and connects as soon as it's detected.

| Button | Key | Action |
|---|---|---|
| **↻ Pivoter** (rotate) | `R` | rotates the picture a quarter turn (remembered) |
| **Photo** | `Space` | saves the displayed picture as JPEG |
| **● Enregistrer** / **■ Arrêter** (record / stop) | `V` | records an MP4 video (plays in QuickTime) |
| **Diffuser** / **■ Stop diffusion** (broadcast) | `D` | sends the picture over the local network (see below) |
| **Dossier** (folder) | | opens the photos and videos folder |
| **? Aide** (help) | `H` | full user guide, inside the app (in French) |

Photos and videos go to the **ProbeView folder on your Desktop** (`~/Desktop/ProbeView`), with the chosen rotation. Rotation is locked while recording. On the first capture, macOS may ask whether ProbeView can access your Desktop: allow it.

### Watching on another device or in OBS

Click **Diffuser** (broadcast) in the app. It keeps working normally (photos, videos) and also publishes the picture on your local network. The bottom of the window shows:

- the **web page address** (e.g. `http://192.168.1.42:8080`): click it, or type it in the browser of a phone or computer **on the same network**;
- the **Copier l'adresse OBS** (copy OBS address) button, which copies the video stream address (`…/stream.mjpg`).

> **The first time**, macOS asks "Allow ProbeView to find devices on local networks?": click **Allow**, otherwise other devices get nothing. If you declined: System Settings → Privacy & Security → **Local Network** → turn ProbeView on.

**In OBS Studio**: Sources → **+** → **Media Source** → uncheck *Local File* → paste the copied address into *Input* → if no picture shows, set *Input Format* to `mjpeg`.
**In VLC**: *File → Open Network* → paste the address.

The port is `8080`; if it's taken, ProbeView uses the next one (`8081`…): the address shown is always the right one. The web page has its own **Pivoter** (rotate), **Plein écran** (fullscreen) and **Capture** (snapshot) buttons.

<details>
<summary>Without the app: server only (start-server.command)</summary>

Handy on a headless Mac or for permanent use. Quit the ProbeView app first (only one program can use the camera at a time), then in Terminal:

```bash
bash ~/Downloads/probeview-main/start-server.command
```

The browser opens and Terminal prints the network address. `Ctrl-C` to stop. The page picks the camera up again after unplugging.

| Command | Effect |
|---|---|
| `PORT=9000 bash start-server.command` | use another port |
| `NO_BROWSER=1 bash start-server.command` | don't open the browser |
| `bash start-server.command --host 127.0.0.1` | only reachable from this Mac |

URLs: `/` viewer page · `/stream.mjpg` video stream · `/snapshot.jpg` latest frame.
</details>

### Update / uninstall

- **Update**: download the ZIP again (or `git pull`), then run `install.command` again. The app is replaced.
- **Uninstall**: move **ProbeView** (in Applications) and the `probeview-main` folder to the Trash. Rotation setting: `~/Library/Application Support/ProbeView`. Homebrew tools stay installed; they do no harm.

### Good to know

- **Real resolution: 640×480.** Listings often claim "HD 1920×1440 / 2 MP". The official apps do save files that size, but they are just upscaled: the camera only sends 640×480 and the app's captures hold no extra detail. ProbeView gives the same quality as the official app.
- **Dual lens**: according to the manufacturer, a long press on the camera button switches lenses. It happens inside the camera; nothing to do in ProbeView.
- **Security**: broadcasting has no password. Anyone on your local network who knows the address can see the picture. On a public network (hotel, station…), don't turn on **Diffuser** (server only: `--host 127.0.0.1`).

### Troubleshooting

| Problem | Fix |
|---|---|
| Double-clicking a `.command` file is refused ("unidentified developer") | Normal for a downloaded file: run it from Terminal with `bash ` in front, as shown above. |
| `No such file or directory` when installing | The folder isn't in Downloads or has another name: use the "`bash ` + drag the file" trick. |
| Install fails | Run it again (it picks up where it stopped); check your Internet connection. |
| App: "Aucun endoscope détecté" (no endoscope detected) | Check the cable (data, not charge-only) and accept "allow accessory": the app connects as soon as the camera is detected. |
| App: "Caméra indisponible (déjà utilisée…)" (camera in use) | Stop `start-server.command` (`Ctrl-C` in Terminal): the app then connects by itself. |
| Broadcast: nothing on the phone or in OBS | Same network? **Local Network** permission granted (System Settings → Privacy & Security → Local Network)? Using the address shown at the bottom of the app? |
| Camera stops responding / frozen picture | Unplug and replug the endoscope. |
| Can't find photos / videos | **Dossier** (folder) button, or the *ProbeView* folder on your Desktop. |
| Picture is sideways | **Pivoter** (rotate) button or `R` key. |
| Server only: "Caméra non connectée" (camera not connected) | Cable, replug, and make sure the ProbeView app is closed. |
| Server only: "port 8080 déjà utilisé" (port in use) | `PORT=9000 bash start-server.command` |
| Server only: page won't open from the phone | Same Wi-Fi? Incoming connections allowed for Python (System Settings → Network → Firewall)? |

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
