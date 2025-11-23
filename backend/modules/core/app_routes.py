# Backend/modules/core/app_routes.py

import json
import os
import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from . import shared_state as g
from .utils_backend import log_function_call

from .database_handler import get_all_player_statistics

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

# Die socketio-Instanz wird hier erstellt und dann von den Handlern importiert
socketio = SocketIO(app, async_mode="gevent", cors_allowed_origins="*", path='/api/socket.io/')

# --- Globale Objekte für den Rest der Anwendung verfügbar machen ---
g.socketio = socketio
g.game_data_lock = threading.RLock()

# ==========================================================
# === Routen-Handler (nur @app.route) ===
# ==========================================================

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

@app.route('/api/statistics')
@app.route('/api/statistics/')
@log_function_call
def statistics_view():
    """
    Liefert aggregierte Statistiken aller Spieler als JSON.
    """
    try:
        stats = get_all_player_statistics()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Fehler in statistics_view: {e}")
        return jsonify({'error': str(e)}), 500

# WICHTIG: Importiere die Socket.IO-Handler am Ende, damit sie sich
# bei der `socketio`-Instanz (die in dieser Datei erstellt wird) registrieren können.
from . import socketio_backend_frontend