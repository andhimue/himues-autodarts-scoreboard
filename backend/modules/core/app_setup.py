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
from ..autodarts.autodarts_websocket import connect_autodarts

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
    if g.USE_DATABASE and g.DATABASE_TYPE == 'mariadb':
        db_required_vars = [
            'DB_USER',
            'DB_PASSWORD',
            'DB_HOST',
            'DB_DATABASE',
            'DB_PORT'
        ]
        for var in db_required_vars:
            value = getattr(g, var, None)

            if var != "DB_PASSWORD":
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

def init_base_app(is_gunicorn):
    """
    Führt die grundlegende Initialisierung aus: Logging, Konfiguration laden, Banner anzeigen.
    Keine Netzwerkverbindungen.
    """
    setup_logger()
    
    os.environ['SSL_CERT_FILE'] = certifi.where()
    g.BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    
    load_and_parse_config()
    _validate_configuration()
    atexit.register(shutdown_cleanup)

    gunicorn_msg = 'RUNNING MODE: Gunicorn' if is_gunicorn else 'RUNNING MODE: Direct execution'

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

#--------------------------------------

def start_network_services():
    """Initialisiert alle ausgehenden Netzwerkverbindungen (Keycloak, WebSocket)."""
    try:
        logging.info("Starte Netzwerkdienste...")
        security_module.start()
        connect_autodarts(g.AUTODARTS_CERT_CHECK)
        logging.info("✅ Netzwerkdienste erfolgreich gestartet.")
    except Exception as e:
        logging.error("Initialisierung der Netzwerkdienste fehlgeschlagen: %s", e)
        sys.exit(1)

#--------------------------------------

def initialize_application():
    """
    Haupt-Initialisierungsfunktion für Gunicorn, die alles in der richtigen Reihenfolge ausführt.
    """
    is_gunicorn = "gunicorn" in sys.argv[0]
    init_base_app(is_gunicorn)
    # Bei Gunicorn erfolgt die Zertifikatsprüfung in der gunicorn.conf.py,
    # daher können die Netzwerkdienste direkt gestartet werden.
    start_network_services()