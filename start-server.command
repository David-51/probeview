#!/bin/bash
# start-server.command — launch the ProbeView web viewer.
#
# Double-click it in Finder, or run it from a terminal:
#   ./start-server.command                 # port 8080, opens the browser
#   PORT=9000 ./start-server.command       # another port
#   NO_BROWSER=1 ./start-server.command    # don't open the browser
#   ./start-server.command --host 127.0.0.1   # extra args go to server.py
#
# Ctrl-C (or closing the Terminal window) stops the server.

set -u
cd "$(dirname "$0")" || exit 1

PORT="${PORT:-8080}"
PY=".venv/bin/python"

pause_exit() {
  echo
  read -r -p "Appuyez sur Entrée pour fermer…" _
  exit "${1:-1}"
}

# 1. Python environment (created on first run).
if [ ! -x "$PY" ]; then
  echo "Création de l'environnement Python (.venv)…"
  python3 -m venv .venv || { echo "ERREUR : python3 introuvable."; pause_exit; }
fi
if ! "$PY" -c 'import numpy, cv2, usb' 2>/dev/null; then
  echo "Installation des dépendances…"
  "$PY" -m pip install -q -r requirements.txt || { echo "ERREUR : installation des dépendances."; pause_exit; }
fi

# 2. libusb backend.
if ! "$PY" -c 'import upp_camera, sys; sys.exit(upp_camera._backend() is None)' 2>/dev/null; then
  echo "ERREUR : libusb introuvable. Installez-le avec :  brew install libusb"
  pause_exit
fi

# 3. Already running? Just open it.
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -s -m 2 "http://localhost:$PORT/status.json" | grep -q '"connected"'; then
    echo "ProbeView tourne déjà sur le port $PORT."
    [ -z "${NO_BROWSER:-}" ] && open "http://localhost:$PORT"
    pause_exit 0
  fi
  echo "ERREUR : le port $PORT est déjà utilisé par un autre programme."
  echo "Relancez avec un autre port, ex. :  PORT=9000 ./start-server.command"
  pause_exit
fi

# 4. Open the browser once the server answers.
if [ -z "${NO_BROWSER:-}" ]; then
  (
    for _ in $(seq 1 40); do
      if curl -s -m 1 "http://localhost:$PORT/status.json" >/dev/null; then
        open "http://localhost:$PORT"
        break
      fi
      sleep 0.5
    done
  ) &
fi

# 5. Run the server in the foreground (prints the LAN URLs).
exec "$PY" server.py --port "$PORT" "$@"
