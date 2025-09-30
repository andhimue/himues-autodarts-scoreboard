# Backend/modules/core/shared_state.py

# Dieses Modul enthält alle globalen Variablen, die von verschiedenen
# Teilen der Anwendung gemeinsam genutzt werden.

# ==============================================================================
# === 1. BENUTZER-KONFIGURATION (Wird beim Start geladen und ist dann konstant) ===
# ==============================================================================
VERSION = "1.2"
DEBUG   = 0  # 0 = kein Debugging, höhere Zahlen für weitere Stufen

# --- Autodarts Konfiguration ---
AUTODARTS_USER_EMAIL     = None
AUTODARTS_USER_PASSWORD  = None
AUTODARTS_BOARD_ID       = None
AUTODARTS_CERT_CHECK     = True


# --- Datenbank Konfiguration ---
USE_DATABASE             = None
DB_USER                  = ''
DB_PASSWORD              = ''
DB_HOST                  = ''
DB_PORT                  = 3306

# --- Webserver & Spiel-Konfiguration ---
SUPPORTED_GAME_VARIANTS  = ['Bull-off', 'X01', 'Cricket/Tactics', "Bermuda", "Shanghai", "Gotcha", "Around the Clock", "Round the World", "Count Up", "Segment Training", "Bob's 27"]
WEBSERVER_DISABLE_HTTPS  = None
WEBSERVER_HOST_IP        = None
WEBSERVER_HOST_PORT      = None
X01_DISPLAY_MODE         = None #cards oder table für die Anzeige im unteren Bereich in X01 und gotcha

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
AUTODARTS_USERS_URL      = 'https://api.autodarts.io/as/v0/users/'
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


FIELD_COORDS = {
    "0":   {"x": 0.016160134143785285,  "y": 1.1049884720184449},       "S1":  {"x": 0.2415216935652902,    "y": 0.7347516243974009},
    "D1":  {"x": 0.29786208342066656,   "y": 0.9359673024523162},       "T1":  {"x": 0.17713267658771747,   "y": 0.5818277090756655},
    "S2":  {"x": 0.4668832529867955,    "y": -0.6415636134982183},      "D2":  {"x": 0.5876126598197445,    "y": -0.7783902745755609},
    "T2":  {"x": 0.35420247327604254,   "y": -0.4725424439320897},      "S3":  {"x": 0.008111507021588693,  "y": -0.7864389016977573},
    "D3":  {"x": -0.007985747222804492, "y": -0.9715573255082791},      "T3":  {"x": -0.007985747222804492, "y": -0.5932718507650387},
    "S4":  {"x": 0.6439530496751206,    "y": 0.4530496751205198},       "D4":  {"x": 0.7888283378746596,    "y": 0.5657304548312723},
    "T4":  {"x": 0.48298050723118835,   "y": 0.36451477677635713},      "S5":  {"x": -0.23334730664430925,  "y": 0.7508488786417943},
    "D5":  {"x": -0.31383357786627536,  "y": 0.9279186753301195},       "T5":  {"x": -0.1850555439111297,   "y": 0.5737790819534688},
    "S6":  {"x": 0.7888283378746596,    "y": -0.013770697966883233},    "D6":  {"x": 0.9739467616851814,    "y": 0.010375183399706544},
    "T6":  {"x": 0.5956612869419406,    "y": -0.005722070844686641},    "S7":  {"x": -0.4506602389436176,   "y": -0.6335149863760215},
    "D7":  {"x": -0.5713896457765667,   "y": -0.7703416474533641},      "T7":  {"x": -0.3540767134772585,   "y": -0.4725424439320897},
    "S8":  {"x": -0.7323621882204988,   "y": -0.239132257388388},       "D8":  {"x": -0.9255292391532174,   "y": -0.2954726472437643},
    "T8":  {"x": -0.5713896457765667,   "y": -0.18279186753301202},     "S9":  {"x": -0.627730035631943,    "y": 0.4691469293649132},
    "D9":  {"x": -0.7726053238314818,   "y": 0.5657304548312723},       "T9":  {"x": -0.48285474743240414,  "y": 0.34841752253196395},
    "S10": {"x": 0.7244393208970865,    "y": -0.23108363026619158},     "D10": {"x": 0.9256549989520018,    "y": -0.28742402012156787},
    "T10": {"x": 0.5715154055753511,    "y": -0.19084049465520878},     "S11": {"x": -0.7726053238314818,   "y": -0.005722070844686641},
    "D11": {"x": -0.9657723747642004,   "y": -0.005722070844686641},    "T11": {"x": -0.5955355271431566,   "y": 0.0023265562775099512},
    "S12": {"x": -0.4506602389436176,   "y": 0.6140222175644519},       "D12": {"x": -0.5633410186543703,   "y": 0.7910920142527772},
    "T12": {"x": -0.3540767134772585,   "y": 0.4932928107315028},       "S13": {"x": 0.7244393208970865,    "y": 0.24378536994340808},
    "D13": {"x": 0.917606371829805,     "y": 0.308174386920981},        "T13": {"x": 0.5634667784531546,    "y": 0.18744498008803193},
    "S14": {"x": -0.7223277562650692,   "y": 0.2440637100898663},       "D14": {"x": -0.9255292391532174,   "y": 0.308174386920981},
    "T14": {"x": -0.5713896457765667,   "y": 0.19549360721022835},      "S15": {"x": 0.6278557954307273,    "y": -0.46449381680989327},
    "D15": {"x": 0.7888283378746596,    "y": -0.5771745965206456},      "T15": {"x": 0.4910291343533851,    "y": -0.34376440997694424},
    "S16": {"x": -0.6196814085097464,   "y": -0.4725424439320897},      "D16": {"x": -0.7967512051980717,   "y": -0.5610773422762524},
    "T16": {"x": -0.49090337455460076,  "y": -0.33571578285474746},     "S17": {"x": 0.2415216935652902,    "y": -0.730098511842381},
    "D17": {"x": 0.29786208342066656,   "y": -0.9152169356529029},      "T17": {"x": 0.18518130370991423,   "y": -0.5691259693984492},
    "S18": {"x": 0.48298050723118835,   "y": 0.6462167260532384},       "D18": {"x": 0.5554181513309578,    "y": 0.799140641374974},
    "T18": {"x": 0.3292712798530314,    "y": 0.49608083282302506},      "S19": {"x": -0.2586037966932027,   "y": -0.7658909981628906},
    "D19": {"x": -0.3134721371708513,   "y": -0.9148193508879362},      "T19": {"x": -0.19589712186160443,  "y": -0.562094304960196},
    "S20": {"x": 0.00006123698714003468,"y": 0.7939375382731171},       "D20": {"x": 0.01119619445411297,   "y": 0.9726766446223462},
    "T20": {"x": 0.00006123698714003468,"y": 0.6058175137783223},       "25":  {"x": 0.06276791181873864,   "y": 0.01794243723208814},
    "50": {"x": -0.007777097366809472,  "y": 0.0022657685241886157},
}

