# Frontend/app.py

# Der Patch MUSS die allererste Code-Zeile sein.
import gevent.monkey
gevent.monkey.patch_all()

import logging
import requests
import threading
import ssl
import signal
import os
import sys
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import socketio as sio_module

# Konfiguration und Hilfsfunktionen importieren
from config_frontend import *

# gevent-spezifische Imports
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from gevent.pywsgi import WSGIServer
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker
from geventwebsocket.handler import WebSocketHandler
import logging

# Importiere das neue shared_state Modul
import modules.core.shared_state_frontend as g

# --- Setup (Warnings, Logging, Custom Classes) ---
urllib3.disable_warnings(InsecureRequestWarning)

# ====================================================
# === Eigene Server-Klasse zur Fehlerunterdrückung ===
# ====================================================
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

#---------------------------------

game_lock = threading.Lock()

# --- Erstellung der Kern-Objekte der Anwendung ---
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = "application/json; charset=utf-8"

# ANPASSUNG: async_mode auf 'gevent' umstellen
socketio_server = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# --- Socket.IO Client zum Verbinden mit dem Backend ---
http_session_for_client = requests.Session()
http_session_for_client.verify = False
sio_client = sio_module.Client(
    http_session=http_session_for_client,
    logger=False, engineio_logger=False, reconnection=True, reconnection_delay=5
)

# --- WICHTIG: Registriere die Kern-Objekte im shared_state ---
g.socketio_server = socketio_server
g.sio_client = sio_client
g.DataFromBackend = {}
g.SUPPORTED_GAME_VARIANTS = []

#---------------------------------

@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache'
    return response

#---------------------------------

# --- Event-Handler für die Verbindung zum Backend ---
@sio_client.event
def connect():
    """
    Wird bei JEDER erfolgreichen Verbindung zum Backend ausgeführt (initial und bei Wiederverbindung).
    Initialisiert den Zustand der Web-Clients.
    """
    logging.info(f"✅ Verbindung zum Backend wss://{g.SERVER_ADDRESS} hergestellt!")
    g.is_backend_connected = True

    try:
        # 1. Hole die Spielmodi
        api_url = f"https://{g.SERVER_ADDRESS}/api/supported-modes"
        response = requests.get(api_url, verify=False, timeout=5)
        response.raise_for_status()

        game_modes = response.json()
        g.SUPPORTED_GAME_VARIANTS.clear()
        g.SUPPORTED_GAME_VARIANTS.extend(game_modes)

        # Setze den globalen Zustand auf "verbunden"
        g.is_backend_connected = True
        
        # 2. Sende das "backend_connected" Event mit den Modi an den Browser
        g.socketio_server.emit('backend_connected', {'modes': game_modes})

        # 3. Logge das Banner in der Konsole
        is_gunicorn = "gunicorn" in sys.argv[0]
        gunicorn_msg = 'RUNNING MODE: Gunicorn' if is_gunicorn else 'RUNNING MODE: Direct execution'
        spielmodi_msg = '✅ Unterstützte Spielmodi erfolgreich vom Backend geladen.'

        # Das Banner wird jetzt auch bei Wiederverbindung geloggt, was nützlich ist.
        banner_message = f"\n--- Backend (wieder) verbunden ---"
        logging.info(banner_message)
        logging.info(f"SUPPORTED GAME-VARIANTS: {', '.join(g.SUPPORTED_GAME_VARIANTS)}")
        logging.info(spielmodi_msg)

        # 4. Hole den aktuellen Spielzustand
        state_url = f"https://{g.SERVER_ADDRESS}/api/current-game-state"
        state_response = requests.get(state_url, verify=False, timeout=5)
        state_response.raise_for_status()

        with game_lock:
            g.DataFromBackend = state_response.json()

        if g.DataFromBackend:
            logging.info("✅ Aktueller Spielzustand vom Backend synchronisiert.")
            g.socketio_server.emit('status_update', g.DataFromBackend)

    except requests.exceptions.RequestException as e:
        logging.error(f"FEHLER bei der Initialisierung nach Verbindung: {e}")
        g.socketio_server.emit('backend_disconnected')


#---------------------------------

@sio_client.event
def disconnect():
    """Wird ausgeführt, wenn die Verbindung zum Backend verloren geht."""
    logging.warning("🔌 Verbindung zum Darts-Hub (Backend) verloren!")

    # Setze den globalen Zustand auf "nicht verbunden"
    g.is_backend_connected = False

    # Sende ein Event an alle verbundenen Browser-Clients
    g.socketio_server.emit('backend_disconnected')

#---------------------------------

@sio_client.on('game-update')
@sio_client.on('match-started')
@sio_client.on('match-ended')
def on_backend_events(data):
    """Empfängt alle relevanten Events vom Backend."""
    if g.DEBUG:
        logging.info(f"DEBUG: Event vom Backend empfangen: {data}")
    with game_lock:
        g.DataFromBackend = data.copy()
    g.socketio_server.emit('status_update', data)

#---------------------------------
# --- Routen und Event-Handler für Browser-Clients ---
#---------------------------------
@app.route('/')
def index():
    """Zeigt die Hauptseite an und steuert die Feuerwerk-Logik."""
    use_video = g.SHOW_ONLY_FIREWORK_VIDEO
    if not use_video:
        user_agent = request.headers.get('User-Agent', '').lower()
        for browser_name in g.BROWSER_NAMES_TO_SHOW_ONLY_VIDEO:
            if browser_name.lower() in user_agent:
                use_video = True
                logging.info(f"✅ '{browser_name}' im User Agent erkannt. Wechsle zu Video-Feuerwerk.")
                break
    return render_template('scoreboard.html', game_modes=g.SUPPORTED_GAME_VARIANTS, force_stable_sorting=g.FORCE_STABLE_SORTING, show_player_card=g.SHOW_PLAYER_CARD, use_video_fireworks=use_video)


#------------------------------------------

@app.route('/status')
@app.route('/status/')
def status():
    """Stellt den aktuellen Spielstatus als JSON-Endpunkt zur Verfügung."""
    with game_lock:
        return jsonify(g.DataFromBackend)

#---------------------------------

@app.route('/static/images:*')
@app.route('/static/videos:*')
def static_files(filename):
    response = send_from_directory('static', filename)
    response.cache_control.max_age = 31536000
    response.cache_control.immutable = True
    return response

#---------------------------------

@socketio_server.on('connect')
def handle_browser_connect():
    """Sendet den initialen Spielstatus an einen neuen Browser."""
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unbekannt')
    logging.info(f'✅ NEW CLIENT CONNECTED: IP: {ip_address} - User Agent: {user_agent}')

    # --- ANPASSUNG START ---
    # Prüfe, ob das Frontend bereits mit dem Backend verbunden ist.
    if g.is_backend_connected:
        # Wenn ja, sende das Event sofort an NUR DIESEN neuen Client.
        if g.DEBUG:
            logging.info("Backend ist bereits verbunden. Sende 'backend_connected' an neuen Client.")
        # 'to=request.sid' stellt sicher, dass nur der neue Client die Nachricht bekommt.
        g.socketio_server.emit('backend_connected', {'modes': g.SUPPORTED_GAME_VARIANTS}, to=request.sid)
    # --- ANPASSUNG ENDE ---

    with game_lock:
        data_copy = g.DataFromBackend.copy()
    g.socketio_server.emit('status_update', data_copy, to=request.sid)

######################################################
# --- Block für den direkten Start (ohne Gunicorn) ---
######################################################
if __name__ == "__main__":
    # Importiere die Initialisierungsfunktion hier, um sie aufzurufen
    from modules.core.app_setup_frontend import initialize_application
    initialize_application()

    ssl_args = {}
    try:
        base_dir = os.path.dirname(os.path.realpath(__file__))
        path_to_crt = os.path.join(base_dir, "crt", "dummy.crt")
        path_to_key = os.path.join(base_dir, "crt", "dummy.key")

        if not g.WEBSERVER_DISABLE_HTTPS_FRONTEND and os.path.exists(path_to_crt) and os.path.exists(path_to_key):
            ssl_args['certfile'] = path_to_crt
            ssl_args['keyfile'] = path_to_key
            logging.info("✅ SSL-Zertifikate gefunden. Starte Server im HTTPS-Modus.")
        else:
            logging.warning("⚠️ Keine SSL-Zertifikate im 'crt'-Ordner gefunden. Starte Server im HTTP-Modus.")
    except Exception as e:
        logging.error(f"Fehler beim Laden der SSL-Zertifikate: {e}")

    logging.info(f"Flask-SocketIO-Server startet auf {g.FLASK_HOST}:{g.FLASK_PORT}")

    http_server = CustomWSGIServer(
        (g.FLASK_HOST, int(g.FLASK_PORT)),
        app,
        handler_class=WebSocketHandler,
        **ssl_args
    )

    def shutdown_server():
        logging.warning("Shutdown-Signal empfangen...")
        server_greenlet.kill()

    gevent.signal_handler(signal.SIGINT, shutdown_server)
    gevent.signal_handler(signal.SIGTERM, shutdown_server)

    server_greenlet = gevent.spawn(http_server.serve_forever)
    server_greenlet.join()
