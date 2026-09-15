#!/bin/bash
# install.command — install ProbeView.app into /Applications.
#
# From Terminal (works even for a downloaded ZIP):
#   bash install.command
# or double-click it in Finder.
#
# Steps: Homebrew -> libusb + Python 3.13 + Tk -> Python environment (.venv)
#        -> build ProbeView.app (PyInstaller) -> copy to /Applications -> open it.
# Safe to run again: it updates the app.

set -u
cd "$(dirname "$0")" || exit 1

PYVER="3.13"
APP_NAME="ProbeView"
DEST="/Applications/$APP_NAME.app"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
fail() {
  printf '\n\033[31mERREUR / ERROR : %s\033[0m\n' "$1"
  read -r -p "Appuyez sur Entrée pour fermer / Press Enter to close…" _
  exit 1
}

echo "Installation de ProbeView / Installing ProbeView"

[ "$(uname)" = "Darwin" ] || fail "ProbeView ne fonctionne que sur macOS / macOS only."

# 1. Homebrew ---------------------------------------------------------------
step "1/5 Homebrew"
for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  [ -x "$b" ] && eval "$("$b" shellenv)" && break
done
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew n'est pas installé. Il sert à installer libusb et Python."
  echo "Homebrew is not installed. It is used to install libusb and Python."
  read -r -p "L'installer maintenant ? / Install it now? [o/y/N] " ans
  case "$ans" in
    [oOyY]*) ;;
    *) fail "Homebrew est nécessaire : https://brew.sh / Homebrew is required." ;;
  esac
  echo "Votre mot de passe de session va être demandé / Your login password will be asked."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
    || fail "installation de Homebrew / Homebrew install failed."
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$b" ] && eval "$("$b" shellenv)" && break
  done
  command -v brew >/dev/null 2>&1 || fail "Homebrew introuvable après installation / not found after install."
fi
echo "OK : $(brew --version | head -1)"

# 2. libusb + Python + Tk -------------------------------------------------------
step "2/5 libusb, Python $PYVER, Tk"
for f in libusb "python@$PYVER" "python-tk@$PYVER"; do
  if brew list --versions "$f" >/dev/null 2>&1; then
    echo "OK : $f"
  else
    brew install "$f" || fail "brew install $f"
  fi
done
PY="$(brew --prefix "python@$PYVER")/bin/python$PYVER"
LIBUSB="$(brew --prefix libusb)/lib/libusb-1.0.dylib"
[ -x "$PY" ] || fail "Python $PYVER introuvable / not found ($PY)."
[ -f "$LIBUSB" ] || fail "libusb introuvable / not found ($LIBUSB)."

# 3. Python environment ---------------------------------------------------------
step "3/5 Environnement Python / Python environment"
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import tkinter' 2>/dev/null; then
  echo "Environnement existant sans Tk : recréation / existing environment lacks Tk: recreating."
  rm -rf .venv
fi
if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv || fail "création de .venv / creating .venv"
fi
.venv/bin/python -m pip install -q --upgrade pip >/dev/null 2>&1
.venv/bin/python -m pip install -q -r requirements.txt pyinstaller \
  || fail "installation des dépendances Python / installing Python packages"
.venv/bin/python -c 'import tkinter, cv2, numpy, usb, PIL' \
  || fail "dépendances incomplètes / missing packages"

# 4. Build ----------------------------------------------------------------------
step "4/5 Fabrication de l'application / Building the app (1-2 min)"
.venv/bin/pyinstaller --windowed --noconfirm --clean --log-level WARN --name "$APP_NAME" \
  --osx-bundle-identifier io.github.david-51.probeview \
  --add-binary "$(readlink -f "$LIBUSB" 2>/dev/null || echo "$LIBUSB"):." app.py \
  || fail "PyInstaller"
[ -d "dist/$APP_NAME.app" ] || fail "dist/$APP_NAME.app absent"
# Text shown by macOS when "Diffuser" asks for the Local Network permission.
PLIST="dist/$APP_NAME.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSLocalNetworkUsageDescription" "$PLIST" 2>/dev/null
/usr/libexec/PlistBuddy -c "Add :NSLocalNetworkUsageDescription string \
Nécessaire pour le bouton « Diffuser » : envoyer l’image de l’endoscope aux appareils de votre réseau local (téléphone, OBS…). \
Needed by the Diffuser (broadcast) button to send the endoscope picture to devices on your local network." "$PLIST" \
  || fail "Info.plist"
codesign --force --deep --sign - "dist/$APP_NAME.app" 2>/dev/null || fail "codesign"

# 5. Install ----------------------------------------------------------------------
step "5/5 Copie dans Applications / Copying to Applications"
while pgrep -f "$APP_NAME.app/Contents/MacOS/$APP_NAME" >/dev/null; do
  read -r -p "Quittez ProbeView puis appuyez sur Entrée / Quit ProbeView, then press Enter… " _ \
    || fail "ProbeView est ouvert / ProbeView is running."
done
if ! { rm -rf "$DEST" && ditto "dist/$APP_NAME.app" "$DEST"; } 2>/dev/null; then
  echo "Droits administrateur nécessaires / Administrator rights needed."
  sudo rm -rf "$DEST" && sudo ditto "dist/$APP_NAME.app" "$DEST" \
    || fail "copie dans /Applications / copying to /Applications"
fi

printf '\n\033[32mProbeView est installé dans Applications. / ProbeView is installed in Applications.\033[0m\n'
echo "Branchez l'endoscope, puis ouvrez ProbeView (Launchpad, Spotlight ou Dock)."
echo "Plug in the endoscope, then open ProbeView (Launchpad, Spotlight or Dock)."
[ -z "${NO_OPEN:-}" ] && open "$DEST"
read -r -p "Appuyez sur Entrée pour fermer / Press Enter to close…" _
exit 0
