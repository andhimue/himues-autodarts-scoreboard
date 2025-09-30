# Backend/gunicorn.conf.py

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
# Gunicorn sucht relativ zum Startverzeichnis, daher ist der Pfad einfach
if not g.WEBSERVER_DISABLE_HTTPS:
    certfile = "crt/dummy.crt"
    keyfile = "crt/dummy.key"

# Die Initialisierung findet jetzt sicher innerhalb jedes Workers statt.
def post_fork(server, worker):
    from modules.core.app_setup import initialize_application
    initialize_application()
