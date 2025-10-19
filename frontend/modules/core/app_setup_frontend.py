# Frontend/modules/core/app_setup_frontend.py

import gevent
import logging
import requests
import sys
import os
import platform

# Importiere urllib3 und die spezifische Warnung
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Unterdrücke die Warnung global für diese Anwendung
urllib3.disable_warnings(InsecureRequestWarning)

from .config_loader_frontend import load_and_parse_config_frontend
from .utils_frontend import setup_logger

import modules.core.shared_state_frontend as g

#---------------------------------

def start_darts_client():
    """
    Stellt in einer robusten Schleife die initiale Verbindung zum Backend her.
    """
    backend_address = f"{g.BACKEND_HOST}:{g.BACKEND_PORT}"
    backend_url = f'wss://{backend_address}'
    api_url = f"https://{backend_address}/api/supported-modes"
    connect_options = {
        'transports': ['websocket'],
        'socketio_path': '/api/socket.io/',
        'headers': {'User-Agent': 'Himues-Autodarts-Scoreboard'}
    }

    while True:
        try:
            if not g.sio_client.connected:
                logging.info(f"Versuche, initiale Verbindung zum Backend herzustellen: {backend_url}")
                g.sio_client.connect(backend_url, **connect_options)
            
            logging.info("Verbindung erfolgreich. Rufe unterstützte Spielmodi ab...")
            response = requests.get(api_url, verify=False, timeout=5)
            response.raise_for_status()
            
            game_modes = response.json()
            g.SUPPORTED_GAME_VARIANTS.clear()
            g.SUPPORTED_GAME_VARIANTS.extend(game_modes)
            
            g.socketio_server.emit('backend_connected', {'modes': game_modes})
            break 
            
        except Exception as e:
            logging.error(f"Initiale Verbindung fehlgeschlagen: {e}")
            logging.info("Nächster Versuch in 3 Sekunden...")
            gevent.sleep(3)

#---------------------------------

def init_base_app():
    """Lädt die Konfiguration und initialisiert das Logging."""
    load_and_parse_config_frontend()
    setup_logger()

#---------------------------------

def start_network_services():
    """Startet die ausgehenden Netzwerkverbindungen (den Client zum Backend)."""
    is_gunicorn = "gunicorn" in sys.argv[0]
    gunicorn_msg = 'RUNNING MODE: Gunicorn' if is_gunicorn else 'RUNNING MODE: Direct execution'

    banner_message = f"""

##################################################
        WELCOME TO HIMUES-Scoreboard-Frontend
##################################################
VERSION: {g.VERSION or "nicht gesetzt"}
RUNNING OS: {platform.system()} | {os.name} | {platform.release()}
SUPPORTED GAME-VARIANTS: {", ".join(g.SUPPORTED_GAME_VARIANTS) if g.SUPPORTED_GAME_VARIANTS else "noch nicht geladen"}

{gunicorn_msg}
"""
    logging.info(banner_message)
    
    # Startet den Verbindungsversuch als Hintergrund-Task
    g.socketio_server.start_background_task(target=start_darts_client)

#---------------------------------

def initialize_application():
    """
    Haupt-Initialisierungsfunktion für Gunicorn, die alles in der richtigen Reihenfolge ausführt.
    """
    init_base_app()
    # Bei Gunicorn erfolgt die Zertifikatsprüfung in der gunicorn.conf.py,
    # daher können die Netzwerkdienste direkt gestartet werden.
    start_network_services()