# Backend/modules/core/web_server_handler.py

import json
import os
import queue
import threading
import logging
import time
from   flask import Flask, render_template, request, jsonify
from   flask_socketio import SocketIO
from   flask_cors import CORS


from . import shared_state as g
from . import constants as c
from .utils_backend import log_function_call, unicast
from ..autodarts.local_board_client import (
    start_board, stop_board, reset_board, calibrate_board,
    restart_board, get_config, patch_config, get_stats, get_cams_stats, get_cams_state
)
from ..autodarts.autodarts_api_client import (
    fetch_and_update_board_address, correct_throw, start_match, 
    next_game, request_next_player, undo_throw
)
# --- Initialisierung von Flask und SocketIO ---

# Den absoluten Pfad zum Hauptverzeichnis (Backend/) ermitteln
# Wir gehen von der aktuellen Datei zwei Ebenen nach oben.
backend_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Die Pfade zu den Ordnern explizit definieren
static_folder_path = os.path.join(backend_root_path, 'static')
template_folder_path = os.path.join(backend_root_path, 'templates')

# Flask mit den korrekten Pfaden initialisieren
app = Flask(__name__,
            static_folder=static_folder_path,
            template_folder=template_folder_path)

CORS(app)
app.config['SECRET_KEY'] = 'himues-dartsscorer for autodarts'

socketio = SocketIO(app, async_mode="gevent", cors_allowed_origins="*", path='/api/socket.io/')

# --- Globale Objekte für den Rest der Anwendung verfügbar machen ---
g.socketio = socketio
g.game_data_lock = threading.RLock()

# ==========================================================
# === Routen- und Event-Handler ===
# ==========================================================

#----------------------------------------------------

@app.route('/api')
@app.route('/api/')
@log_function_call
def api_index_view():
    """Rendert eine Übersichtsseite für alle API- und Debug-Endpunkte."""
    return render_template('api_index.html')

#----------------------------------------------------

@app.route('/api/supported-modes')
@app.route('/api/supported-modes/')
@log_function_call
def get_supported_modes():
    """Gibt die Liste der unterstützten Spielmodi als JSON zurück.
       Hierrüber fragt das Frontend die evrfügbaren Spielmodi ab,
       die es auf seienr Statseite anzeigt.
    """
    return jsonify(g.SUPPORTED_GAME_VARIANTS)
    
#----------------------------------------------------

@app.route('/api/debug')
@app.route('/api/debug/')
@log_function_call
def debug_view():
    """Rendert die Debug-Webseite, die vom Backend an das Frontend gesendete 
       Events anzeigt.
    """
    return render_template('debug.html')

#----------------------------------------------------

@app.route('/api/debugad')
@app.route('/api/debugad/')
@log_function_call
def debugad_view():
    """Rendert die Debug-Webseite für die Rohdaten, die vom Autodarts-Server 
       empfangen werden.
    """
    return render_template('debugad.html')

@app.route('/api/debugadall')
@app.route('/api/debugadall/')
@log_function_call
def debugadall_view():
    """Rendert die Debug-Webseite für die ungefilterten Rohdaten, die vom 
       Autodarts-Server empfangen werden.
    """
    return render_template('debugadall.html')
    
#----------------------------------------------------

@app.route('/api/state')
@app.route('/api/state/')
def debug_state_view():
    """Rendert eine Debug-Seite, die den aktuellen Zustand aller globalen 
       Variablen aus dem shared_state (g) anzeigt. Interne oder sensible 
       Variablen werden dabei ausgeschlossen.
    """
    state_data = {}
    
    # Gehe durch alle Attribute des 'g'-Moduls
    for key in dir(g):
        # Filtere interne Python-Attribute und Module heraus
        if key.startswith('__') or key in ['socketio', 'logger', 'game_data_lock', 'ws_greenlet', 'server_greenlet', 'keycloak_client', 'ad_debug_log', 'debug_log', 'FIELD_COORDS', 'autodarts_raw_log', 'last_websocket_message'] or 'PASSWORD' in key.upper():
            continue

        value = getattr(g, key)

        formatted_value = ""
        if isinstance(value, (dict, list)):
            # Formatiere Dictionaries und Listen mit Einrückung
            try:
                formatted_value = json.dumps(value, indent=4, ensure_ascii=False, default=str)
            except TypeError:
                formatted_value = repr(value) # Fallback, falls nicht JSON-serialisierbar
        else:
            # Stelle alle anderen Werte als String dar
            formatted_value = repr(value)

        state_data[key] = formatted_value

    # Übergebe die formatierten Daten an das neue Template
    return render_template('debug_state.html', state_data=state_data)

#----------------------------------------------------

@app.route('/api/current-game-state')
@app.route('/api/current-game-state/')
@log_function_call
def get_current_game_state():
    # Auf eine Anfrage des Browsers hin senden wir hier das zuletzt ans Frontend gsendete Event erneut.
    # Falls ein Frontend sich neu verbindet (nach Neustart oder Verbindungsabbruch,
    # kann es den aktuellen Zustand abfragen)
    return jsonify(g.last_message_to_frontend or {}) 

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

         # HGibt die Board-Adresse 1:1 aus dem globalen State zurück.
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

#----------------------------------------------------

@socketio.on('message')
@log_function_call
def handle_message(message):
    """Verarbeitet eingehende Nachrichten von einem Socket.IO-Client.
       also Befehle, die potenziell von der Weboberfläche kommen könnten (wie "next", "undo", "board-start")

       Fungiert als Dispatcher, der die Nachricht analysiert und an die 
       entsprechende Handler-Funktion (_handle_board_command, 
       _handle_correct_command, etc.) weiterleitet.

       Args:
           message (str): Die vom Client gesendete Nachricht, z.B. "board-start" oder "correct:0:T20".
    """
    try:
        if not isinstance(message, str):
            # Ignoriere Nachrichten, die kein String sind (z.B. Dictionarys)
            return

        # Hole die ID des Absenders einmal zentral am Anfang
        cid = str(request.sid)
        
        # Finde den Hauptbefehl
        command = message.split(':')[0]

        # Das Dispatcher-Dictionary
        command_handlers = {
            c.CMD_BOARD_START:     _handle_board_command,
            c.CMD_BOARD_STOP:      _handle_board_command,
            c.CMD_BOARD_RESET:     _handle_board_command,
            c.CMD_BOARD_CALIBRATE: _handle_board_command,
            c.CMD_CORRECT:         _handle_correct_command,
            c.CMD_NEXT:            _handle_next_command,
            c.CMD_UNDO:            lambda msg, sid: undo_throw(),
            c.CMD_HELLO:           _handle_hello_command
        }

        # Finde den passenden Handler
        handler = command_handlers.get(command)
        if handler:
            # Rufe den Handler immer mit beiden Parametern auf
            handler(message, cid)

    except Exception as e:
        logging.error('WS-Client-Message failed: %s', e)
        
#----------------------------------------------------

def _handle_board_command(message, sid):
    """Verarbeitet alle 'board-*' Befehle, die von handle_message 
       weitergeleitet werden.

        Args:
            message (str): Die vollständige Befehlsnachricht, z.B. "board-start:0.5".
            sid (str):     Die Session-ID des anfragenden Clients (wird hier nicht verwendet).
    """
    fetch_and_update_board_address()
    if g.boardManagerAddress:
        if message.startswith(c.CMD_BOARD_START):
            parts = message.split(':')
            wait = float(parts[1]) if len(parts) > 1 else 0.5
            time.sleep(wait)
            start_board()
        elif message == c.CMD_BOARD_STOP: stop_board()
        elif message == c.CMD_BOARD_RESET: reset_board()
        elif message == c.CMD_BOARD_CALIBRATE: calibrate_board()

#----------------------------------------------------

def _handle_correct_command(message, sid):
    """Verarbeitet den 'correct'-Befehl zum Korrigieren eines Wurfs.

        Args:
            message (str): Die Korrekturnachricht im Format "correct:<index>:<score>", z.B. "correct:0:T20".
            sid (str):     Die Session-ID des anfragenden Clients (wird hier nicht verwendet).
    """
    _, *indices, score = message.split(':')
    correct_throw(indices, score)

#----------------------------------------------------

def _handle_next_command(message, sid):
    """Verarbeitet den 'next'-Befehl, der entweder ein Match startet oder zum 
        nächsten Spiel/Leg wechselt.

        Args:
            message (str): Die Befehlsnachricht ("next").
            sid (str):     Die Session-ID des anfragenden Clients (wird hier nicht verwendet).
    """
    if g.active_match_id:
        if g.active_match_id.startswith('lobby'):
            start_match(g.active_match_id.split(':')[1])
        else:
            next_game()

#----------------------------------------------------

def _handle_hello_command(message, sid):
    """Verarbeitet den 'hello'-Befehl eines neuen Clients.

        Sendet eine 'welcome'-Nachricht per Unicast an den Client zurück, um die
        Kommunikation zu bestätigen.

        Args:
            message (str): Die Befehlsnachricht ("hello").
            sid (str):     Die Session-ID des anfragenden Clients.
    """
    unicast(sid, {c.KEY_EVENT: c.EVT_WELCOME})