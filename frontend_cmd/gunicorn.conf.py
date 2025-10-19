# CMD_Frontend/gunicorn.conf.py

import os
import sys

from modules.core.config_loader_cmd import load_and_parse_config
from modules.core import shared_state_cmd as g

load_and_parse_config()

# Netzwerkeinstellungen
bind = f"{g.FLASK_HOST}:{g.FLASK_PORT}"

# Worker-Prozesse
workers = 1
# Der Worker muss zum async_mode ('gevent') passen
worker_class = "app_cmd.CustomGeventWebSocketWorker"

# Logging
loglevel = 'info' # 'info' ist besser für die Fehlersuche
accesslog = "-"
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


# KORREKTUR: Stabiler Gunicorn-Hook zum Starten von Hintergrund-Tasks
def post_fork(server, worker):
    """Wird nach dem Start eines Workers ausgeführt."""
    from modules.core.socketio_cmd_backend import initialize_application
    initialize_application()