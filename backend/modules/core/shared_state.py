# Backend/modules/core/shared_state.py

# Dieses Modul enthält alle globalen Variablen, die von verschiedenen
# Teilen der Anwendung gemeinsam genutzt werden.

# ==============================================================================
# === 1. BENUTZER-KONFIGURATION (Wird beim Start geladen und ist dann konstant) ===
# ==============================================================================
VERSION = "1.3"
DEBUG   = 0  # 0 = kein Debugging, höhere Zahlen für weitere Stufen

# --- Autodarts Konfiguration ---
AUTODARTS_USER_EMAIL     = None
AUTODARTS_USER_PASSWORD  = None
AUTODARTS_BOARD_ID       = None
AUTODARTS_CERT_CHECK     = True


# --- Datenbank Konfiguration ---
USE_DATABASE             = None
DATABASE_TYPE            = 'mariadb' # mariadb oder sqlite
DB_USER                  = ''
DB_PASSWORD              = ''
DB_HOST                  = ''
DB_PORT                  = 3306
DB_DATABASE              = ''

# --- Webserver & Spiel-Konfiguration ---
SUPPORTED_GAME_VARIANTS  = ['Bull-off', 'X01', 'Cricket/Tactics', "Bermuda", "Shanghai", "Gotcha", "Around the Clock", "Round the World", "Count Up", "Segment Training", "Bob's 27"]

# Platzhalter für Zertifikatspfade
CERT_FILE                = None
KEY_FILE                 = None

WEBSERVER_HOST_IP        = None
WEBSERVER_HOST_PORT      = None

# --- Weiteres ---
BACKEND_DIR = None                  # Variable für den absoluten Pfad zum Backend-Verzeichnis
RECONNECT_MATCH_MAX_AGE_HOURS = 2   # Wenn das Backend während eines laufenden Spiels gestartet wird, soll es das Spiel nur anzeigen, wenn es noch nicht älter als 2 Stunden ist

# ==============================================================================
# === 2. ECHTE KONSTANTEN (Ändern sich nie) ===
# ==============================================================================
AUTODARTS_URL            = "https://autodarts.io"
AUTODARTS_AUTH_URL       = "https://login.autodarts.io"
AUTODARTS_LOBBIES_URL    = 'https://api.autodarts.io/gs/v0/lobbies/'
AUTODARTS_MATCHES_URL    = 'https://api.autodarts.io/gs/v0/matches/'
AUTODARTS_BOARDS_URL     = 'https://api.autodarts.io/bs/v0/boards/'
#AUTODARTS_USERS_URL      = 'https://api.autodarts.io/as/v0/users/'
AUTODARTS_USERS_URL      = 'https://api.autodarts.io/us/v0/users/'
AUTODARTS_WEBSOCKET_URL  = 'wss://api.autodarts.io/ms/v0/subscribe'

# --- Geteilte Applikations-Objekte (Platzhalter) ---
# Werden durch das Programm gesetzt. Müssen nicht in config.py definiert werden
ad_debug_log             = []   # Speichert die formatierten Log-Einträge für die /debugad-Webseite (Autodarts-Rohdaten).
autodarts_raw_log        = []   # Speichert alle rohen, ungefilterten WebSocket-Nachrichten vom Autodarts-Server.
boardManagerAddress      = None # Speichert die ermittelte IP-Adresse des lokalen Board-Managers.
debug_log                = []   # Speichert die Log-Einträge für die /debug-Webseite (Backend -> Frontend Events).
game_data_lock           = None # Ein Threading-Lock, um den konkurrierenden Zugriff auf geteilte Zustandsvariablen zu verhindern.
logger                   = None # Der globale Logger für die Anwendung zur Ausgabe von Informationen auf der Konsole.
socketio                 = None # Die Flask-SocketIO-Server-Instanz für die Kommunikation mit den Clients.
ws_greenlet              = None # Der gevent-Greenlet, der die persistente WebSocket-Verbindung zu Autodarts verwaltet.

# Globale Variablen für die Token-Laufzeiten
token_access_expires_in  = "N/A"
token_refresh_status     = "N/A"

# --- Geteilte Match- und Spiel-Zustandsvariablen ---
# Werden durch das Programm gesetzt oder verwenden diese Werte. Müssen nicht in config.py definiert werden
active_match_id          = None # Speichert die ID des aktuell laufenden Matches oder der aktiven Lobby.
last_websocket_message   = None # Speichert die letzte WebSocket-Nachricht, um doppelte Verarbeitungen zu vermeiden.
last_message_to_frontend = {}   # Speichert die zuletzt ans Frontend gesendete Message oder ein leeres Element
player_data_map          = {}   # In-Memory-Cache für spielerbezogene Daten (Typ, Gesamt-Average, Indizes)
processed_leg_ids        = set() # Ein Set, das sich die IDs der bereits gespeicherten Legs merkt (z.B. "matchid-1", "matchid-2")
bull_off_winner          = None # Gewinner des Ausbullens
checkoutsCounter         = {}   # Zählt die Checkout-Versuche pro Spieler.
lobbyPlayers             = []   # Speichert eine Liste der Spieler, die sich aktuell in einer Lobby befinden.

# --- Caching für Last Turn Darts ---
last_throw_cache = {}       # Speichert den letzten abgeschlossenen Wurf pro Spieler: { "PlayerName": "T20, 20, 5" }
current_turn_throws = {}    # Speichert die laufenden Würfe des aktuellen Spielers: { "PlayerName": "T20..." }
previous_player_index = -1  # Um den Spielerwechsel zu erkennen
current_leg_index = 0

