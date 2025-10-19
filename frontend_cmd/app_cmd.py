# frontend_cmd/app_cmd.py

# Der Patch MUSS die allererste Code-Zeile sein.
import gevent.monkey
gevent.monkey.patch_all()

import os
import sys
import ssl
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker

# Importiere die App-Instanz und die Initialisierungsfunktion aus den neuen Modulen
from modules.core.app_routes_cmd import app
from modules.core.socketio_cmd_backend import initialize_application
import modules.core.shared_state_cmd as g

# --- Eigene Server-Klassen zur Fehlerunterdrückung ---
class CustomWSGIServer(WSGIServer):
    def wrap_socket_and_handle(self, client_socket, address):
        try:
            super().wrap_socket_and_handle(client_socket, address)
        except (ssl.SSLEOFError, ssl.SSLZeroReturnError, ssl.SSLError):
            pass

class CustomGeventWebSocketWorker(GeventWebSocketWorker):
    server_class = CustomWSGIServer

# --- Haupt-Ausführungsblock für direkten Start ---
if __name__ == '__main__':
    # 1. Basiskonfiguration laden
    # ANPASSUNG: Wir rufen hier nur einen Teil der Initialisierung auf
    from modules.core.config_loader_cmd import load_and_parse_config
    load_and_parse_config()

    # 2. Zertifikate prüfen (VOR dem Start der Netzwerkdienste)
    print("Prüfe SSL-Zertifikate...")
    try:
        base_dir = os.path.dirname(os.path.realpath(__file__))
        path_to_crt = os.path.join(base_dir, g.CERT_FILE)
        path_to_key = os.path.join(base_dir, g.KEY_FILE)

        if not (os.path.exists(path_to_crt) and os.path.exists(path_to_key)):
            print(f"FEHLER: Zertifikatsdateien nicht gefunden unter '{path_to_crt}' und '{path_to_key}'.")
            sys.exit(1)
        
        print("✅ SSL-Zertifikate gefunden.")
        ssl_args = {'certfile': path_to_crt, 'keyfile': path_to_key}

    except Exception as e:
        print(f"FEHLER beim Laden der Zertifikate: {e}")
        sys.exit(1)
    
    # 3. Erst jetzt die Netzwerkdienste (und den Rest) initialisieren
    initialize_application()
    
    # 4. Webserver starten
    print(f"Starte Webserver auf https://{g.FLASK_HOST}:{g.FLASK_PORT}")
    http_server = CustomWSGIServer(
        (g.FLASK_HOST, g.FLASK_PORT), app,
        handler_class=WebSocketHandler, **ssl_args
    )
    http_server.serve_forever()