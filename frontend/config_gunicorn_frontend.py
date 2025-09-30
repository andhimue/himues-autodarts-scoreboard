# Frontend/gunicorn_conf_frontend.py

# Importiere den neuen Loader und das shared_state Modul
from modules.core.config_loader_frontend import load_and_parse_config_frontend
from modules.core import shared_state_frontend as g

# Lade die Werte in den globalen Zustand
load_and_parse_config_frontend()

preload_app = False

# Netzwerkeinstellungen dynamisch aus der Konfiguration erstellen
bind = f"{g.FLASK_HOST}:{g.FLASK_PORT}"

workers = 1
worker_class = "app_frontend.CustomGeventWebSocketWorker"

# Setzt den Log-Level. 'warning' unterdrückt INFO-Meldungen wie "Handling signal".
loglevel = 'warning'

# Deaktiviert das Access-Log komplett. Dies verhindert die Ausgabe von
# "GET /static/..."-Zeilen.
accesslog = None

# Diese Zeile sorgt dafür, dass echte Fehler weiterhin auf der Konsole angezeigt werden.
errorlog = "-" 

certfile = None
keyfile = None

if not g.WEBSERVER_DISABLE_HTTPS:
    certfile = "crt/dummy.crt"
    keyfile  = "crt/dummy.key"
    
# Gunicorn-Hook, der nach dem Start eines Workers ausgeführt wird
def post_fork(server, worker):
    """
    Diese Funktion wird einmal pro Worker-Prozess aufgerufen.
    Sie ist der perfekte Ort für unsere Initialisierungslogik.
    """
    # Importiere und rufe die Initialisierung aus dem stabilen Pfad auf.
    from modules.core.app_setup_frontend import initialize_application
    initialize_application()