#!/bin/bash

# Den Ordner finden, in dem das Skript liegt
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Den Pfad zum Python-Interpreter im venv-Ordner zusammenbauen
# Geht vom Skript-Ordner eine Ebene nach oben zum Projekt-Root
VENV_PYTHON="$SCRIPT_DIR/../venv/bin/python3"

# Die Anwendung mit dem korrekten Python-Interpreter aus der venv starten
# Ersetze 'app_backend.py' durch den jeweiligen Dateinamen
"$VENV_PYTHON" "$SCRIPT_DIR/app_cmd.py" 2>&1

