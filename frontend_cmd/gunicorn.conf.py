# CMD_Frontend/gunicorn.conf.py

from modules.core.config_loader_cmd import load_and_parse_config
from modules.core import shared_state_cmd as g

load_and_parse_config()

# Netzwerkeinstellungen
bind = f"{g.FLASK_HOST}:{g.FLASK_PORT}"

# Worker-Prozesse
workers = 1
# KORREKTUR: Der Worker muss zum async_mode ('gevent') passen
worker_class = "app_cmd.CustomGeventWebSocketWorker"

# Logging
loglevel = 'info' # 'info' ist besser für die Fehlersuche
accesslog = "-"
errorlog = "-"

# SSL-Einstellungen
if not g.WEBSERVER_DISABLE_HTTPS:
    certfile = "crt/dummy.crt"
    keyfile = "crt/dummy.key"

# KORREKTUR: Stabiler Gunicorn-Hook zum Starten von Hintergrund-Tasks
def post_fork(server, worker):
    """Wird nach dem Start eines Workers ausgeführt."""
    from app_cmd import initialize_application
    initialize_application()