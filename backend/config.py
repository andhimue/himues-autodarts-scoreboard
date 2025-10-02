# Backend/config.py
# Zentrale Konfigurations- und Standardwerte für das Backend


#Die folgenden Werte könenn auch in einr Datei .env im Hauptverzeichnis des Backends konfiguriert werden
AUTODARTS_USER_EMAIL=""
AUTODARTS_USER_PASSWORD=""
AUTODARTS_BOARD_ID=""
AUTODARTS_CLIENT_ID = ""
AUTODARTS_CLIENT_SECRET=""

AUTODARTS_CERT_CHECK = False

# Steuert, ob die Datenbank für Statistiken verwendet wird.
USE_DATABASE = True

DB_USER = ''
DB_PASSWORD = ''
DB_HOST = ''
DB_PORT = 3306
DB_DATABASE = ''

DEBUG = 0  # 0 = kein Debugging, höhere Zahlen für weitere Stufen

WEBSERVER_DISABLE_HTTPS=False
WEBSERVER_HOST_IP = '0.0.0.0'
WEBSERVER_HOST_PORT = 6001

