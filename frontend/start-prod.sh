#!/bin/bash

# Den Ordner finden, in dem das Skript liegt
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Den Pfad zu gunicorn im venv-Ordner zusammenbauen
VENV_GUNICORN="$SCRIPT_DIR/../venv/bin/gunicorn"

#Es gibt beim Beenden des gunicorn Servers ein Traceback. Das ist aber im Endeffekt nur eine harmlose Infomeldung, die hier unterdrückt wird.
echo "Starte Gunicorn mit: $VENV_GUNICORN"
"$VENV_GUNICORN" -c "$SCRIPT_DIR/config_gunicorn_frontend.py" "app_frontend:app" 2>&1 | grep -v "SystemExit"
