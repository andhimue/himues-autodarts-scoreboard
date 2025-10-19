# CMD_Frontend/config_cmd.py

# --- Flask Server Einstellungen ---
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 6003

# Pfade für SSL-Zertifikate
CERT_FILE = "crt/dummy.crt"
KEY_FILE = "crt/dummy.key"


# --- Backend Adresse ---
# Die Adresse deines Haupt-Backends (himues-scoreboard-backend)
SERVER_ADDRESS = "10.0.1.112:6001"