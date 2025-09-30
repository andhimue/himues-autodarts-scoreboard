# Frontend/config_frontend.py

import logging

# ==============================================================================
# 2. Konfiguration
# ==============================================================================
FLASK_HOST = '0.0.0.0'
FLASK_PORT = '6002'
FLASK_DEBUG = False

SERVER_ADDRESS = "127.0.0.1:6001"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

WEBSERVER_DISABLE_HTTPS_FRONTEND = False

SUPPORTED_GAME_VARIANTS = []

DEBUG=0

# Bei True wird IMMER das Feruerwerk-Video verwendet und fireworks.js nie geladen.
SHOW_ONLY_FIREWORK_VIDEO = False

# Eine Liste von Texten. Wenn einer davon im User Agent des Browsers
# gefunden wird, wird ebenfalls das Video anstelle von fireworks.js verwendet.
BROWSER_NAMES_TO_SHOW_ONLY_VIDEO = ["Tizen 5.0"]
