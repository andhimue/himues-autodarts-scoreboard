# Frontend/config_frontend.py

import logging

# @hidden
# WICHTIG: Ein geheimer Schlüssel ist für die Session-Verwaltung des Editors erforderlich.
# @hidden
# Ändern Sie diesen in eine lange, zufällige Zeichenkette.
# @hidden
SECRET_KEY = "ersetze-mich-durch-einen-zufaelligen-geheimen-schluessel"

# @hidden
# Wenn CONFIG_EDITOR_USER leer ist, wird keine Passwortabfrage angezeigt.
# @hidden
CONFIG_EDITOR_USER = ""
# @hidden
CONFIG_EDITOR_PASSWORD = ""

# Lokaler Webserver
WEBSERVER_HOST = "0.0.0.0"
WEBSERVER_PORT = 6002

# Backend (0.0.0.0 = erreichbar auf allen IP-Adressen)
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 6001

# Logging
# @hidden
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# Steuert die Anzeige der Spieldauer
SHOW_MATCH_DURATION = True # Steuert ob die Spieldauer überhaupt angezeigt wird
SHOW_DURATION_IN_GAMERULES = True # True= Anzeige als Teil der Spielregeln, False = Anzeige oben rechts
MATCH_DURATION_INTERVAL = 5 # Intervall für die Aktualisierung der Spieldaueranzeige in Sekunden (z.B. 5, 10, 15)

# Pfade für SSL-Zertifikate
CERT_FILE = "crt/dummy.crt"
KEY_FILE = "crt/dummy.key"

#Debug-Möglichkeit
DEBUG = False

# Feuerwerk als Gewinner-Anzeige
SHOW_ONLY_FIREWORK_VIDEO = False # Bei True wird IMMER das Feruerwerk-Video verwendet und fireworks.js nie geladen.

# Eine Liste von Texten. Wenn einer davon im User Agent des Browsers
# gefunden wird, wird ebenfalls das Video anstelle von fireworks.js verwendet.
BROWSER_NAMES_TO_SHOW_ONLY_VIDEO = ["Tizen 5.0", "Tizen 4.0"]

# Steuert die Standard-Sortierung der Spielerliste im Frontend.

FORCE_STABLE_SORTING = True # True: Stabile Sortierung, False: Rotiertende Server-Reihenfolge (siehe Doku))

# Mit True werden die Spieler in X01 und Gotcha als Karte angezeigt.
# Mit False als Tabelle
SHOW_PLAYER_CARD = False

# Liste von Spielernamen, die in der Statistik ausgeblendet werden sollen
STATS_IGNORE_PLAYERS = ["einer", "noch einer", "Bot Level 1", "Bot Level 2"]
