# frontend_cmd/modules/core/socketio_cmd_backend.py

# Importiert die Instanzen aus der app_routes_cmd.py
from .app_routes_cmd import sio_client, socketio_server
import modules.core.shared_state_cmd as g
from modules.core.config_loader_cmd import load_and_parse_config

# --- Gekapselte Initialisierungs-Logik ---
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
    """
    Bündelt die Initialisierungslogik.
    Wird von Gunicorn (post_fork) oder vom __main__-Block aufgerufen.
    """
    # Stelle sicher, dass die Konfiguration geladen ist
    if g.FLASK_HOST is None:
        load_and_parse_config()
        
    # Startet den Verbindungsversuch als Hintergrund-Task
    socketio_server.start_background_task(target=start_backend_client)

# --- Event-Handler ---
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