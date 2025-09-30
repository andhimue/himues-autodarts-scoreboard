import logging
import os
import requests
from datetime import datetime, timezone
import hmac
import hashlib
from dotenv import load_dotenv
from pathlib import Path

from ..core import shared_state as g
from ..autodarts.autodarts_keycloak_client import AutodartsKeycloakClient

# --- Interne, private Variablen des Moduls ---
_ACCESS_TOKEN = "HIER_IHR_EIGENES_TOKEN_EINFUEGEN"
_SECRET_SERVER_URLS = [
    "https://ihr-server1.com/get-secrets",
    "https://ihr-server2.com:9000/get-secrets"
]
_keycloak_client = None

#--------------------------------------------------------------------------------------

# --- Interne Hilfsfunktionen ---
def _verify_project_integrity():
    # ... (Diese Funktion bleibt exakt gleich wie zuvor)
    try:
        expected_line = 'EVT_MATCH_STARTED="match-started"'
        current_dir = os.path.dirname(__file__)
        target_file_path = os.path.join(current_dir, 'constants.py')
        if not os.path.exists(target_file_path):
             print("Integritätsprüfung fehlgeschlagen. Prüfziel nicht gefunden.")
             return False
        with open(target_file_path, 'r') as f:
            for line in f:
                if expected_line in line.replace(" ", "").replace("'", '"'):
                    return True
    except Exception as e:
        print(f"Integritätsprüfung fehlgeschlagen: {e}")
        return False
    print("Integritätsprüfung fehlgeschlagen.")
    return False

#--------------------------------------------------------------------------------------

# --- Öffentliche Funktionen des Moduls ---
def start():
    """
    Initialisiert das Security-Modul: Prüft Integrität, versucht, Secrets von einer Liste
    von Servern zu laden und startet den internen Keycloak-Client.
    """
    global _keycloak_client
    client_id = None
    client_secret = None

    if not _verify_project_integrity():
        print("FATAL: Die Anwendung scheint unvollständig oder modifiziert zu sein.")
        exit(1)

    # --- KOMBINIERTE LOGIK ZUR BESCHAFFUNG DER SECRETS ---

    # Priorität 1: Versuche, aus .env-Datei zu laden
    load_dotenv()
    client_id = os.getenv("AUTODARTS_CLIENT_ID")
    client_secret = os.getenv("AUTODARTS_CLIENT_SECRET")

    if client_id and client_secret:
        logging.info("✅ Secrets erfolgreich aus '.env'-Datei geladen.")
    
    # Priorität 2: Wenn in .env nicht erfolgreich, versuche aus config.py zu laden
    if not (client_id and client_secret):
        logging.info("Secrets konnten nicht aus '.env' gelesen werden, prüfe 'config.py'")
        try:
            config_path = Path(__file__).parent.parent.parent / 'config.py'
            if config_path.is_file():
                config_code = config_path.read_text()
                local_scope = {}
                exec(config_code, {}, local_scope)
                
                config_id = local_scope.get('AUTODARTS_CLIENT_ID')
                config_secret = local_scope.get('AUTODARTS_CLIENT_SECRET')

                if config_id and config_secret:
                    client_id = config_id
                    client_secret = config_secret
                    logging.info("✅ Secrets erfolgreich aus 'config.py' geladen.")
        except Exception as e:
            logging.warning(f"Secrets konnten nicht aus 'config.py' gelesen werden: {e}. Überspringe.")

    # Priorität 3: Wenn immer noch nicht erfolgreich, frage die Remote-Server ab (Fallback)
    if not (client_id and client_secret):
        logging.info("Keine lokalen Secrets gefunden. Versuche, Secrets von der Server-Liste abzurufen...")

        # Verwende enumerate, um einen Index (i) für jeden Server zu bekommen
        for i, server_url in enumerate(_SECRET_SERVER_URLS):
            # Erstelle einen generischen Namen wie "Server 1", "Server 2", etc.
            server_name = f"Server{i + 1}"

            try:
                #logging.info(f"Versuche, Secrets von '{server_name}' zu laden...")
                timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M')
                key = _ACCESS_TOKEN.encode('utf-8')
                msg = timestamp.encode('utf-8')
                signature = hmac.new(key, msg, hashlib.sha256).hexdigest()
                headers = {'Authorization': signature, 'X-Request-Timestamp': timestamp}
                
                response = requests.get(server_url, headers=headers, timeout=5)
                response.raise_for_status()
                
                loaded_secrets = response.json()
                temp_client_id = loaded_secrets.get("AUTODARTS_CLIENT_ID")
                temp_client_secret = loaded_secrets.get("AUTODARTS_CLIENT_SECRET")

                if not all([temp_client_id, temp_client_secret]):
                    raise ValueError("Secrets vom Server unvollständig empfangen.")

                client_id = temp_client_id
                client_secret = temp_client_secret
                logging.info(f"✅ Secrets erfolgreich von '{server_name}' geladen.")
                break # Verlasse die Schleife, da die Secrets gefunden wurden
            except Exception as e:
                logging.warning(f"Konnte Secrets von '{server_name}' nicht laden: {e}")
                continue # Mache mit dem nächsten Server weiter
    
    # Finale Prüfung und Initialisierung
    if not all([client_id, client_secret]):
        print("FATAL: Client-ID oder Client-Secret konnten aus keiner Quelle ermittelt werden.\n\rDas BAckend wird beendet.")
        exit(1)

    _keycloak_client = AutodartsKeycloakClient(
        username=g.AUTODARTS_USER_EMAIL,
        password=g.AUTODARTS_USER_PASSWORD,
        client_id=client_id,
        client_secret=client_secret
    )
    _keycloak_client.start()

#--------------------------------------------------------------------------------------

def stop():
    """Stoppt den internen Keycloak-Client sauber."""
    if _keycloak_client:
        _keycloak_client.stop()

#--------------------------------------------------------------------------------------

def get_auth_header():
    """
    Gibt den fertigen, sicheren Header mit dem Autodarts Bearer-Token für 
    normale REST-API-Aufrufe zurück.
    """
    if _keycloak_client and _keycloak_client.access_token:
        return {'Authorization': 'Bearer ' + _keycloak_client.access_token}
    raise Exception("Security Modul nicht initialisiert oder Token nicht verfügbar.")

#--------------------------------------------------------------------------------------

def get_websocket_header():
    """Gibt den fertigen Header für die WebSocket-Verbindung zurück."""
    return get_auth_header()
    
#--------------------------------------------------------------------------------------

def get_user_id():
    """Gibt die User-ID des authentifizierten Benutzers zurück."""
    if _keycloak_client:
        return _keycloak_client.user_id
    return None
