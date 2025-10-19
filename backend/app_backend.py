# Backend/himues-darts-hub.py

# Der Patch MUSS die allererste Code-Zeile sein.
import gevent.monkey
gevent.monkey.patch_all()

import logging
import os
import sys
import signal
import gevent
import ssl
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker

# --- Eigene Module ---
from modules.core.app_routes import app, socketio
from modules.core.app_setup import init_base_app, start_network_services
from modules.core import shared_state as g

#----------------------------------------------------------

# ====================================================
# === Eigene Server-Klasse zur Fehlerunterdrückung ===
# ====================================================
class CustomWSGIServer(WSGIServer):
    # ANPASSUNG: Wir überschreiben nicht mehr handle_error, sondern
    # die Methode, die den SSL-Handshake durchführt.
    def wrap_socket_and_handle(self, client_socket, address):
        """
        Wickelt den Socket in SSL ein und fängt harmlose Fehler ab
        direkt an der Quelle ab.
        """
        try:
            # Versuche, die ursprüngliche Funktion auszuführen
            super().wrap_socket_and_handle(client_socket, address)

        except (ssl.SSLEOFError, ssl.SSLZeroReturnError, ssl.SSLError): #ssl.SSLError verhindert Meldung SSLV3_ALERT_CERTIFICATE_UNKNOWN auf der Konsole
            # Wenn harmlose Fehler auftreten, ignoriere sie einfach
            # und beende die Verarbeitung für diese eine fehlerhafte Verbindung.
            pass

        # Alle anderen, echten Fehler werden weiterhin normal ausgelöst und angezeigt.

# =========================================================
# === Eigener Gunicorn-Worker, der unseren Server nutzt ===
# =========================================================
class CustomGeventWebSocketWorker(GeventWebSocketWorker):
    """
    Dieser Worker erbt vom Standard-Gevent-WebSocket-Worker,
    aber überschreibt die server_class, um unsere CustomWSGIServer-Klasse
    mit der Fehlerunterdrückung zu verwenden.
    """
    server_class = CustomWSGIServer

# ---------------------------------------------------

# Dieser Block wird nur ausgeführt, wenn man "python3 app.py" startet.
# Gunicorn ignoriert diesen Teil.
if __name__ == "__main__":
    # 1. Nur Basiskonfiguration laden (ohne Netzwerk)
    init_base_app(is_gunicorn=False)

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

    # 3. Erst jetzt die Netzwerkdienste starten
    start_network_services()

    # 4. Webserver starten
     # Erstellt eine Instanz unseres eigenen Servers.
    # Wichtig: Wir übergeben die `socketio.handler`, damit der Server
    # weiß, wie er mit WebSocket-Anfragen umgehen soll.
    http_server = CustomWSGIServer(
        (g.WEBSERVER_HOST_IP, g.WEBSERVER_HOST_PORT),
        app,
        handler_class=WebSocketHandler,
        **ssl_args
    )

    def shutdown_server():
        # Diese Funktion beendet nur noch den Server-Greenlet, ohne Ausgabe.
        if hasattr(g, 'server_greenlet'):
            g.server_greenlet.kill()

    gevent.signal_handler(signal.SIGINT, shutdown_server)
    gevent.signal_handler(signal.SIGTERM, shutdown_server)

    g.server_greenlet = gevent.spawn(http_server.serve_forever)

    g.server_greenlet.join()
