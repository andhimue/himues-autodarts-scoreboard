# Frontend/app_frontend.py

# Der Patch MUSS die allererste Code-Zeile sein.
import gevent.monkey
gevent.monkey.patch_all()

import logging
import ssl
import signal
import os
import sys
import gevent
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker

# Importiere die App-Instanz und die Initialisierungsfunktion
from modules.core.app_routes_frontend import app
from modules.core.app_setup_frontend import init_base_app, start_network_services
import modules.core.shared_state_frontend as g

# --- Eigene Server-Klassen zur Fehlerunterdrückung ---
class CustomWSGIServer(WSGIServer):
    def wrap_socket_and_handle(self, client_socket, address):
        """
        Wickelt den Socket in SSL ein und fängt den SSLZeroReturnError
        direkt an der Quelle ab.
        """
        try:
            super().wrap_socket_and_handle(client_socket, address)
        except (ssl.SSLEOFError, ssl.SSLZeroReturnError, ssl.SSLError): #ssl.SSLError verhindert Meldung SSLV3_ALERT_CERTIFICATE_UNKNOWN auf der Konsole
            pass

class CustomGeventWebSocketWorker(GeventWebSocketWorker):
    """
    Dieser Worker erbt vom Standard-Gevent-WebSocket-Worker,
    aber überschreibt die server_class, um unsere CustomWSGIServer-Klasse
    mit der Fehlerunterdrückung zu verwenden.
    """
    server_class = CustomWSGIServer

######################################################
# --- Block für den direkten Start (ohne Gunicorn) ---
######################################################
if __name__ == "__main__":
    # 1. Nur Basiskonfiguration und Logging initialisieren
    init_base_app()

    # 2. Zertifikate prüfen (VOR dem Start der Netzwerkdienste)
    logging.info("Prüfe SSL-Zertifikate...")
    try:
        base_dir = os.path.dirname(os.path.realpath(__file__))
        path_to_crt = os.path.join(base_dir, g.CERT_FILE)
        path_to_key = os.path.join(base_dir, g.KEY_FILE)

        if not (os.path.exists(path_to_crt) and os.path.exists(path_to_key)):
            logging.critical(f"FEHLER: Zertifikatsdateien nicht gefunden unter '{path_to_crt}' und '{path_to_key}'.")
            sys.exit(1)

        logging.info("✅ SSL-Zertifikate gefunden.")
        ssl_args = {'certfile': path_to_crt, 'keyfile': path_to_key}
    except Exception as e:
        logging.error(f"FEHLER beim Laden der Zertifikate: {e}")
        sys.exit(1)

    # 3. Erst jetzt die Netzwerkdienste starten (Verbindung zum Backend)
    start_network_services()

    # 4. Webserver starten
    logging.info(f"Starte Webserver auf https://{g.WEBSERVER_HOST}:{g.WEBSERVER_PORT}")
    http_server = CustomWSGIServer(
        (g.WEBSERVER_HOST, int(g.WEBSERVER_PORT)),
        app,
        handler_class=WebSocketHandler,
        **ssl_args
    )

    # Funktion zum sauberen Herunterfahren
    def shutdown_server():
        logging.warning("Shutdown-Signal empfangen...")
        server_greenlet.kill()

    # Signal-Handler registrieren
    gevent.signal_handler(signal.SIGINT, shutdown_server)
    gevent.signal_handler(signal.SIGTERM, shutdown_server)

    # Server in einem Greenlet starten und darauf warten
    server_greenlet = gevent.spawn(http_server.serve_forever)
    server_greenlet.join()