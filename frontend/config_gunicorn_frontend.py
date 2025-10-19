# Frontend/gunicorn_conf_frontend.py

import os
import sys

# Importiere den neuen Loader und das shared_state Modul
from modules.core.config_loader_frontend import load_and_parse_config_frontend
from modules.core import shared_state_frontend as g

# Lade die Werte in den globalen Zustand
load_and_parse_config_frontend()

preload_app = False

# Netzwerkeinstellungen dynamisch aus der Konfiguration erstellen
bind = f"{g.WEBSERVER_HOST}:{g.WEBSERVER_PORT}"

workers = 1
worker_class = "app_frontend.CustomGeventWebSocketWorker"

# Setzt den Log-Level. 'warning' unterdrückt INFO-Meldungen wie "Handling signal".
loglevel = 'warning'

# Deaktiviert das Access-Log komplett. Dies verhindert die Ausgabe von
# "GET /static/..."-Zeilen.
accesslog = None

# Diese Zeile sorgt dafür, dass echte Fehler weiterhin auf der Konsole angezeigt werden.
errorlog = "-" 

# Die Pfade werden jetzt direkt aus der geladenen Konfiguration übernommen.
try:
    base_dir = os.path.dirname(os.path.realpath(__file__))
    path_to_crt = os.path.join(base_dir, g.CERT_FILE)
    path_to_key = os.path.join(base_dir, g.KEY_FILE)

    if not (os.path.exists(path_to_crt) and os.path.exists(path_to_key)):
        # Farben für die Terminal-Ausgabe definieren
        COLOR_RED = '\033[91m'
        COLOR_BOLD = '\033[1m'
        COLOR_END = '\033[0m'

        error_message = (
            f"{COLOR_RED}{COLOR_BOLD}"
            "################################################################\n"
            "#                      GUNICORN START FEHLER                   #\n"
            "################################################################\n"
            f"  FEHLER: Zertifikatsdateien nicht gefunden!\n\n"
            f"  Gesucht wurde nach:\n"
            f"  - Zertifikat: {path_to_crt}\n"
            f"  - Schlüssel:  {path_to_key}\n\n"
            "  Bitte führen Sie das 'install.py'-Skript aus, um die\n"
            "  Dummy-Zertifikate zu erstellen, oder passen Sie die\n"
            "  Pfade in der config.py an um eigene Zertifikate zu verwenden.\n"
            "################################################################\n"
            f"{COLOR_END}"
        )
        sys.stderr.write(error_message)
        sys.exit(1) # Beendet den Gunicorn-Prozess sauber

    certfile = path_to_crt
    keyfile = path_to_key
except Exception as e:
    sys.stderr.write(f"Ein unerwarteter Fehler ist beim Laden der Zertifikate aufgetreten: {e}\n")
    sys.exit(1)

# Gunicorn-Hook, der nach dem Start eines Workers ausgeführt wird
def post_fork(server, worker):
    """
    Diese Funktion wird einmal pro Worker-Prozess aufgerufen.
    Sie ist der perfekte Ort für unsere Initialisierungslogik.
    """
    # Importiere und rufe die Initialisierung aus dem stabilen Pfad auf.
    from modules.core.app_setup_frontend import initialize_application
    initialize_application()