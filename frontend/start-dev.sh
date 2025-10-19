#!/bin/bash

# Den Ordner finden, in dem das Skript liegt
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Den Pfad zum Python-Interpreter im venv-Ordner zusammenbauen
VENV_PYTHON="$SCRIPT_DIR/../venv/bin/python3"

# Die Anwendung mit dem Python aus der virtuellen Umgebung starten
"$VENV_PYTHON" "$SCRIPT_DIR/app_frontend.py" 2>&1
