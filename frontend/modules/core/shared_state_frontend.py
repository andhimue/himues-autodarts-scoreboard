# Frontend/modules/core/shared_state.py

VERSION="1.3"

# Dieses Modul enthält globale Variablen, die vom Frontend-Dienst geteilt werden.
WEBSERVER_HOST = None
WEBSERVER_PORT = None

BACKEND_HOST = None
BACKEND_PORT = None

CONFIG_EDITOR_USER = None
CONFIG_EDITOR_PASSWORD = None

# Platzhalter für Zertifikatspfade
CERT_FILE                = None
KEY_FILE                 = None

DEBUG = 0

SHOW_MATCH_DURATION              = None
SHOW_DURATION_IN_GAMERULES       = None
MATCH_DURATION_INTERVAL          = None

SHOW_ONLY_FIREWORK_VIDEO         = None
BROWSER_NAMES_TO_SHOW_ONLY_VIDEO = None

# Steuert die Standard-Sortierung der Spielerliste im Frontend.
# True: Stabile Sortierung (nach display_order, wie aktuell).
# False: Rotiertende Server-Reihenfolge (nach Index im players-Array).
FORCE_STABLE_SORTING = True

# Anzeige der Spieler als Karte oder Tabelle
SHOW_PLAYER_CARD = False

# Liste der zu ignorierenden Spieler in der Statistik
STATS_IGNORE_PLAYERS = []

# Mapping für Namensersetzungen
PLAYER_NAME_REPLACEMENTS = {}

# --- Geteilte Applikations-Objekte (Platzhalter) ---
# Werden von app.py beim Start befüllt.
socketio_server         = None
sio_client              = None
logger                  = None

# Globale Variable für den Spielstatus und die Spielmodi
DataFromBackend         = {}
SUPPORTED_GAME_VARIANTS = []


is_backend_connected = False