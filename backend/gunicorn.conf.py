# Backend/gunicorn.conf.py

import os
import sys

from modules.core.config_loader import load_and_parse_config
from modules.core import shared_state as g

# Lade die Werte in den globalen Zustand
load_and_parse_config()

preload_app = True

# Netzwerkeinstellungen dynamisch aus dem globalen Zustand erstellen
bind = f"{g.WEBSERVER_HOST_IP}:{g.WEBSERVER_HOST_PORT}"

# Worker-Prozesse
workers = 1

# Pfad zu unserer neuen Worker-Klasse
# Format: <dateiname>.<klassenname>
worker_class = "app_backend.CustomGeventWebSocketWorker"

# Setzt den Log-Level. 'warning' unterdrückt INFO-Meldungen wie "Handling signal".
loglevel = 'warning'

# Deaktiviert das Access-Log komplett. Dies verhindert die Ausgabe von
# "GET /static/..."-Zeilen.
accesslog = None

# Diese Zeile sorgt dafür, dass echte Fehler weiterhin auf der Konsole angezeigt werden.
errorlog = "-" 

# SSL-Einstellungen für Gunicorn
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

# Die Initialisierung findet jetzt sicher innerhalb jedes Workers statt.
def post_fork(server, worker):
    from modules.core.app_setup import initialize_application
    initialize_application()
