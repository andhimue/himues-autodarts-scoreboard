# Backend/modules/core/app_setup.py

import logging
import atexit
import certifi
import os
import platform
import sys
import logging

from . import shared_state as g
from ..core import security_module
from .config_loader import load_and_parse_config
from .utils_backend import check_already_running, setup_logger
from ..autodarts.autodarts_keycloak_client import AutodartsKeycloakClient
from ..autodarts.websocket_handlers import connect_autodarts

#--------------------------------------

def _validate_configuration():
    """
    Prüft, ob alle notwendigen Konfigurationsvariablen einen gültigen Wert haben.
    Beendet die Anwendung mit einer klaren Fehlermeldung, wenn etwas fehlt.
    """
    missing_vars = []
    
    # Liste der immer benötigten Variablen
    required_vars = [
        'AUTODARTS_USER_EMAIL',
        'AUTODARTS_USER_PASSWORD',
        'AUTODARTS_BOARD_ID'
    ]
    
    for var in required_vars:
        value = getattr(g, var, None)
        # Prüft explizit auf None oder einen leeren String
        if value is None or value == '':
            missing_vars.append(var)

    
    # Bedingte Prüfung für die Datenbank
    if g.USE_DATABASE:
        db_required_vars = [
            'DB_USER',
            'DB_PASSWORD',
            'DB_HOST',
            'DB_DATABASE',
            'DB_PORT'
        ]
        for var in db_required_vars:
            value = getattr(g, var, None)
            logging.info("%s = %s", var, value)
            if value is None or value == '':
                missing_vars.append(var)

    if missing_vars:
        error_message = (
            "\n############################################################\n"
            "FEHLER: Kritische Konfigurationswerte fehlen!\n"
            "Bitte stellen Sie sicher, dass die folgenden Variablen in\n"
            "Ihrer .env- oder config.py-Datei gesetzt sind:\n\n"
            + "\n".join(f"  - {var}" for var in missing_vars) +
            "\n\nAnwendung wird beendet.\n"
            "############################################################"
        )
        logging.critical(error_message)
        sys.exit(1)
    
    logging.info("✅ Konfiguration erfolgreich validiert.")
    
#--------------------------------------

def shutdown_cleanup():
    """Wird bei einem sauberen Herunterfahren des Programms automatisch aufgerufen (via atexit).
        Stellt sicher, dass Hintergrund-Tasks wie der Keycloak-Client und der WebSocket-Greenlet ordnungsgemäß beendet werden.
    """
    sys.stderr.write("\n[SHUTDOWN] Anwendung wird beendet, räume auf...\n")
    if hasattr(security_module, '_keycloak_client') and security_module._keycloak_client:
        security_module.stop()

    if hasattr(g, 'ws_greenlet') and g.ws_greenlet:
        g.ws_greenlet.kill()
        sys.stderr.write("[SHUTDOWN] WebSocket-Client gestoppt.\n")
    sys.stderr.write("[SHUTDOWN] Auf Wiedersehen!\n")
    sys.stderr.flush()

#--------------------------------------

def initialize_application():
    """Führt alle notwendigen Schritte zur Initialisierung der Backend-Anwendung aus.

        Dies umfasst das Laden der Konfiguration, das Einrichten des Loggings, 
        das Starten des Keycloak-Authentifizierungs-Clients und den Aufbau der 
        WebSocket-Verbindung zum Autodarts-Server.
    """
    setup_logger()
    
    os.environ['SSL_CERT_FILE'] = certifi.where()
    g.BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    
    setup_logger()
    is_gunicorn = "gunicorn" in sys.argv[0]
    load_and_parse_config()
    _validate_configuration()
    atexit.register(shutdown_cleanup)

    is_gunicorn = "gunicorn" in sys.argv[0]
    if is_gunicorn:
        gunicorn_msg = 'RUNNING MODE: Gunicorn'
    else:
        gunicorn_msg = 'RUNNING MODE: Direct execution'

    banner_message = f"""

##################################################
        WELCOME TO HIMUES-Scoreboard-Backend
##################################################
VERSION: {g.VERSION or "nicht gesetzt"}
RUNNING OS: {platform.system()} | {os.name} | {platform.release()}
SUPPORTED GAME-VARIANTS: {", ".join(g.SUPPORTED_GAME_VARIANTS)}

{gunicorn_msg}
"""
    logging.info(banner_message)

    if not is_gunicorn and check_already_running():
        sys.exit()

    try:
#        g.keycloak_client = AutodartsKeycloakClient(username=g.AUTODARTS_USER_EMAIL, password=g.AUTODARTS_USER_PASSWORD, client_id=g.AUTODARTS_CLIENT_ID, client_secret=g.AUTODARTS_CLIENT_SECRET, debug=False)
#        g.keycloak_client.start()
        security_module.start()
        connect_autodarts(g.AUTODARTS_CERT_CHECK)
    except Exception as e:
        logging.error("Initialisierung fehlgeschlagen: %s", e)
        sys.exit(1)