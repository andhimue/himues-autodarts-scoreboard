# frontend_cmd/modules/core/app_routes_cmd.py

import os
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO
import socketio as sio_module

import modules.core.shared_state_cmd as g

# Pfade für Templates und Static-Dateien definieren
cmd_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
static_folder_path = os.path.join(cmd_root_path, 'static')
template_folder_path = os.path.join(cmd_root_path, 'templates')

app = Flask(__name__,
            static_folder=static_folder_path,
            template_folder=template_folder_path)

# Wichtig: async_mode auf 'gevent' setzen
socketio_server = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# --- Socket.IO Client zum Backend ---
http_session = requests.Session()
http_session.verify = False
sio_client = sio_module.Client(
    http_session=http_session, logger=False, engineio_logger=False,
    reconnection=True, reconnection_delay=5
)

# --- Routen ---
@app.route('/')
def cmd_page():
    return render_template('cmd.html')

# Wichtig: Importiere die Socket.IO-Handler am Ende
from . import socketio_cmd_backend