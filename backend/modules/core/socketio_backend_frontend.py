# Backend/modules/core/socketio_backend_frontend.py

import logging
from flask import request

# Wichtig: Importiert die socketio-Instanz aus der neuen app_routes.py
from .app_routes import socketio
from . import shared_state as g

from .utils_backend import log_function_call
from ..autodarts.autodarts_local_board_client import (
    start_board, stop_board, reset_board, calibrate_board,
    restart_board, get_config, patch_config, get_stats, get_cams_stats, get_cams_state
)
from ..autodarts.autodarts_api_client import (
    correct_throw, start_match, next_game, request_next_player, undo_throw
)

# ==========================================================
# === Socket.IO Event-Handler ===
# ==========================================================

#----------------------------------------------------

# --- NEUER EVENT-HANDLER FÜR BEFEHLE ---
@socketio.on('command')
@log_function_call
def handle_command(data):
    """
    Empfängt strukturierte JSON-Befehle und sendet die Antwort explizit
    über das 'command_response'-Event zurück.
    """
    sid = request.sid
    action = data.get('action')
    params = data.get('params', {})
    callback_id = data.get('callback_id') # Die ID vom Client

    command_dispatcher = {
        # Befehle für local_board_client.py
        'start_board': start_board,
        'stop_board': stop_board,
        'reset_board': reset_board,
        'calibrate_board': calibrate_board,
        'restart_board': restart_board,
        'get_config': get_config,
        'patch_config': patch_config,
        'get_stats': get_stats,
        'get_cams_state': get_cams_state,
        'get_cams_stats': get_cams_stats,

         # Gibt die Board-Adresse 1:1 aus dem globalen State zurück.
        'get_board_address': lambda: {
            'board_manager_address': g.boardManagerAddress if g.boardManagerAddress else 'N/A'
        },

        # Befehle für autodarts_api_client.py
        'undo_throw': undo_throw,
        'next_player': request_next_player,
        'next_game': next_game,
        'start_match': start_match,
        'correct_throw': correct_throw
    }

    handler = command_dispatcher.get(action)
    result = None

    if handler:
        try:
            result = handler(**params) if params else handler()
            if g.DEBUG >1:
                logging.info("Befehl '%s' vom Frontend erfolgreich ausgeführt.", action)
        except Exception as e:
            logging.error("Fehler bei der Ausführung des Befehls '%s': %s", action, e)
            result = {'error': str(e)}
    else:
        logging.warning("Unbekannter Befehl '%s' vom Frontend empfangen.", action)
        result = {'error': f"Unbekannter Befehl: {action}"}

    # Sende die Antwort nur, wenn der Client eine Callback-ID mitgeschickt hat.
    if callback_id:
        # HIER: Die Antwort wird explizit gesendet
        socketio.emit('command_response', {'callback_id': callback_id, 'data': result}, room=sid)

    # Diese Funktion hat keinen 'return'-Wert mehr.
    
#----------------------------------------------------


@socketio.on('connect')
@log_function_call
def handle_connect():
    """Behandelt den Verbindungsaufbau eines neuen Socket.IO-Clients. Loggt die 
       Session-ID, IP-Adresse und den User-Agent des Clients.
    """
    with g.game_data_lock:
        cid        = str(request.sid)
        ip         = str(request.remote_addr)
        namespace  = str(request.namespace)
        user_agent = request.headers.get('User-Agent', 'Unbekannt')
        
        logging.info('NEW CLIENT CONNECTED to %s: %s - IP: %s - User Agent: %s', namespace, cid, ip, user_agent)

#----------------------------------------------------

@socketio.on('disconnect')
@log_function_call
def handle_disconnect():
    """Behandelt den Verbindungsabbruch eines Socket.IO-Clients und loggt das 
       Ereignis.
    """
    with g.game_data_lock:
        cid = str(request.sid)

        if g.DEBUG > 0:
           logging.info('CLIENT DISCONNECTED: %s', cid)

#----------------------------------------------------

@socketio.on('connect', namespace='/debug')
@log_function_call
def handle_debug_connect():
    """Wird aufgerufen, wenn sich ein Client mit dem '/debug'-Namespace 
       verbindet. Sendet den gesamten bisherigen Debug-Verlauf an den neuen 
       Client.
    """
    if g.DEBUG > 0:
        logging.info('Client connected to /debug namespace.')

    g.socketio.emit('full_log', g.debug_log, namespace='/debug')

#----------------------------------------------------

@socketio.on('connect', namespace='/debugad')
@log_function_call
def handle_debugad_connect():
    """Wird aufgerufen, wenn sich ein Client mit dem '/debugad'-Namespace 
       verbindet. Sendet den gesamten bisherigen Autodarts-Rohdaten-Verlauf an 
       den neuen Client.
    """
    if g.DEBUG > 0:
        logging.info('Client connected to /debugad namespace.')

    if g.ad_debug_log:
        socketio.emit('full_ad_log', g.ad_debug_log, namespace='/debugad', room=request.sid)

#----------------------------------------------------

@socketio.on('connect', namespace='/debugadall')
def handle_debugadall_connect():
    """Wird aufgerufen, wenn sich ein Client mit dem '/debugadall'-Namespace 
       verbindet. Sendet den gesamten bisherigen, ungefilterten 
       Autodarts-Rohdaten-Verlauf an den neuen Client.
    """
    if g.DEBUG > 0:
        logging.info('Client connected to /debugadall namespace.')

    if hasattr(g, 'autodarts_raw_log'):
        # Sende die komplette Liste nur an diesen einen neuen Client
        socketio.emit('full_log', g.autodarts_raw_log, namespace='/debugadall', to=request.sid)