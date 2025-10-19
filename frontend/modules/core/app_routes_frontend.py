# Frontend/modules/core/app_routes_frontend.py

import requests
import threading
import sys
import os  # Hinzugefügt für die Pfad-Ermittlung
from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, session
from flask_socketio import SocketIO
import socketio as sio_module
from config_frontend import SECRET_KEY

# Konfiguration und Hilfsfunktionen importieren
from config_frontend import *
import modules.core.shared_state_frontend as g

# --- Erstellung der Kern-Objekte der Anwendung ---
game_lock = threading.Lock()

# --- ANPASSUNG: Explizite Pfade für Templates und Static-Dateien definieren ---
# Ermittle den Pfad zum Hauptverzeichnis des Frontends (zwei Ebenen nach oben)
frontend_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
static_folder_path = os.path.join(frontend_root_path, 'static')
template_folder_path = os.path.join(frontend_root_path, 'templates')

# Flask mit den korrekten Pfaden initialisieren
app = Flask(__name__,
            static_folder=static_folder_path,
            template_folder=template_folder_path)
            
app.config['SECRET_KEY'] = SECRET_KEY
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
# --- Routen für Browser-Clients ---
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
    return render_template('scoreboard.html', 
        # Variablen, die an das Template übergeben werden
        game_modes=g.SUPPORTED_GAME_VARIANTS, 
        force_stable_sorting=g.FORCE_STABLE_SORTING, 
        show_player_card=g.SHOW_PLAYER_CARD, 
        use_video_fireworks=use_video, 
        debug=g.DEBUG,
        show_match_duration=g.SHOW_MATCH_DURATION,
        show_duration_in_gamerules=g.SHOW_DURATION_IN_GAMERULES,
        match_duration_interval=g.MATCH_DURATION_INTERVAL
    )

#------------------------------------------

#------------------------------------------
# --- NEUE ROUTEN FÜR DEN KONFIGURATIONS-EDITOR ---
#------------------------------------------

@app.route('/config-editor', methods=['GET', 'POST'])
def config_editor():
    """ Zeigt die Konfigurationsseite an und verarbeitet Änderungen. """
    # Die Funktionen werden jetzt hier importiert, direkt bevor sie gebraucht werden.
    from .config_editor import parse_config_file, save_config_file, restart_service, is_running_as_service

    # Prüfe, ob ein Login erforderlich ist UND ob der User eingeloggt ist
    if g.CONFIG_EDITOR_USER and 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        save_config_file(request.form)
        restart_message = restart_service()
        return render_template('editor/config_status.html', message=restart_message)

    # Bei GET-Request:
    config_structure = parse_config_file()
    running_as_service = is_running_as_service()
    return render_template('editor/config_editor.html', structure=config_structure, is_service=running_as_service)

@app.route('/config-editor/cancel')
def config_cancel():
    """ Zeigt eine Status-Seite für den Abbruch an. """
    return render_template('editor/config_cancel.html', message="Änderungen verworfen. Sie werden zur Hauptseite weitergeleitet.")

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ Behandelt den Login für den Konfigurations-Editor. """
    # Wenn kein Benutzer konfiguriert ist, direkt zum Editor weiterleiten
    if not g.CONFIG_EDITOR_USER:
        session['logged_in'] = True
        return redirect(url_for('config_editor'))

    error = None
    if request.method == 'POST':
        if request.form.get('username') == g.CONFIG_EDITOR_USER and request.form.get('password') == g.CONFIG_EDITOR_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('config_editor'))
        else:
            error = 'Ungültige Anmeldedaten. Bitte versuchen Sie es erneut.'
    return render_template('editor/login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

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

# WICHTIG: Importiere die Socket.IO-Handler am Ende, damit sie sich
# bei der `socketio_server`-Instanz registrieren können.
from . import socketio_frontend_backend