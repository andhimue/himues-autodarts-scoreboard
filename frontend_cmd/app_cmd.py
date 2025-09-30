# Der Patch MUSS die allererste Code-Zeile sein.
import gevent.monkey
gevent.monkey.patch_all()

import os
import ssl
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO
import socketio as sio_module

from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker

import modules.core.shared_state_cmd as g
from modules.core.config_loader_cmd import load_and_parse_config

# --- Eigene Server-Klassen (bleiben unverändert) ---
class CustomWSGIServer(WSGIServer):
    def wrap_socket_and_handle(self, client_socket, address):
        try:
            super().wrap_socket_and_handle(client_socket, address)
        except (ssl.SSLEOFError, ssl.SSLZeroReturnError, ssl.SSLError):
            pass

class CustomGeventWebSocketWorker(GeventWebSocketWorker):
    server_class = CustomWSGIServer

# --- Initialisierung ---
load_and_parse_config()
app = Flask(__name__)
# Wichtig: async_mode auf 'gevent' setzen, passend zum Worker
socketio_server = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# --- Socket.IO Client zum Backend ---
http_session = requests.Session()
http_session.verify = False
sio_client = sio_module.Client(
    http_session=http_session, logger=False, engineio_logger=False,
    reconnection=True, reconnection_delay=5
)

# --- NEU: Gekapselte Initialisierungs-Logik ---
def start_backend_client():
    """Baut die Verbindung zum Haupt-Backend auf."""
    try:
        sio_client.connect(
            f'wss://{g.SERVER_ADDRESS}',
            transports=['websocket'],
            socketio_path='/api/socket.io/'
        )
    except Exception as e:
        print(f"Fehler bei initialer Backend-Verbindung (wird im Hintergrund weiter versucht): {e}")

def initialize_application():
    """Startet die Backend-Verbindung als Hintergrund-Task."""
    socketio_server.start_background_task(target=start_backend_client)

# --- Routen und Event-Handler ---
@app.route('/')
def cmd_page():
    return render_template('cmd.html')

@sio_client.event
def connect():
    print(f"✅ Erfolgreich mit dem Backend-Hub ({g.SERVER_ADDRESS}) verbunden!")

@sio_client.event
def disconnect():
    print(f"🔌 Verbindung zum Backend-Hub ({g.SERVER_ADDRESS}) verloren!")

@socketio_server.on('command')
def forward_command_to_backend(data):
    # Zusätzliche Sicherheitsprüfung
    if sio_client.connected:
        sio_client.emit('command', data)
    else:
        print("Befehl konnte nicht weitergeleitet werden: Keine Verbindung zum Backend.")

@sio_client.on('command_response')
def forward_response_to_browser(data):
    socketio_server.emit('command_response', data)

# --- Haupt-Ausführungsblock für direkten Start ---
if __name__ == '__main__':
    initialize_application() # Initialisierung auch hier aufrufen
    ssl_args = {}
    if not g.WEBSERVER_DISABLE_HTTPS:
        cert_path = os.path.join('crt', 'dummy.crt')
        key_path = os.path.join('crt', 'dummy.key')
        if os.path.exists(cert_path) and os.path.exists(key_path):
            ssl_args = {'certfile': cert_path, 'keyfile': key_path}
            print(f"✅ Starte HTTPS-Server auf Port {g.FLASK_PORT}")
        else:
            print(f"⚠️ WARNUNG: Zertifikate nicht gefunden. Starte ungesicherten HTTP-Server.")

    print("Starte CustomWSGIServer...")
    http_server = CustomWSGIServer(
        (g.FLASK_HOST, g.FLASK_PORT), app,
        handler_class=WebSocketHandler, **ssl_args
    )
    http_server.serve_forever()