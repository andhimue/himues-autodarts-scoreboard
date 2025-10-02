# Frontend/modules/core/shared_state.py

VERSION="1.2"

# Dieses Modul enthält globale Variablen, die vom Frontend-Dienst geteilt werden.
FLASK_HOST = None
FLASK_PORT = None
FLASK_DEBUG = None

WEBSERVER_DISABLE_HTTPS = None
DEBUG = 0
SHOW_ONLY_FIREWORK_VIDEO = None
BROWSER_NAMES_TO_SHOW_ONLY_VIDEO = None

# Steuert die Standard-Sortierung der Spielerliste im Frontend.
# True: Stabile Sortierung (nach display_order, wie aktuell).
# False: Rotiertende Server-Reihenfolge (nach Index im players-Array).
FORCE_STABLE_SORTING = True

# Anzeige der Spieler als Karte oder Tabelle
SHOW_PLAYER_CARD = False


# --- Geteilte Applikations-Objekte (Platzhalter) ---
# Werden von app.py beim Start befüllt.
socketio_server         = None
sio_client              = None
logger                  = None

# Globale Variable für den Spielstatus und die Spielmodi
DataFromBackend         = {}
SUPPORTED_GAME_VARIANTS = []


is_backend_connected = False