# Frontend/modules/core/socketio_frontend_backend.py

import logging
import requests
import sys
from flask import request

# Wichtig: Importiert die Instanzen aus der app_routes_frontend.py
from .app_routes_frontend import sio_client, socketio_server, game_lock
import modules.core.shared_state_frontend as g

# --- Event-Handler für die Verbindung zum Backend ---
@sio_client.event
def connect():
    """
    Wird bei JEDER erfolgreichen Verbindung zum Backend ausgeführt (initial und bei Wiederverbindung).
    Initialisiert den Zustand der Web-Clients.
    """
    backend_address = f"{g.BACKEND_HOST}:{g.BACKEND_PORT}"
    logging.info(f"✅ Verbindung zum Backend wss://{backend_address} hergestellt!")
    g.is_backend_connected = True

    try:
        # 1. Hole die Spielmodi
        api_url = f"https://{backend_address}/api/supported-modes"
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
        state_url = f"https://{backend_address}/api/current-game-state"
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
@sio_client.on('match-ended')
def on_backend_events(data):
    """Empfängt alle relevanten Events vom Backend."""
    if g.DEBUG:
        logging.info(f"DEBUG: Event vom Backend empfangen: {data}")
    with game_lock:
        g.DataFromBackend = data.copy()
    socketio_server.emit('status_update', data)

#---------------------------------
# --- Event-Handler für Browser-Clients ---
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
    socketio_server.emit('status_update', data_copy, to=request.sid)