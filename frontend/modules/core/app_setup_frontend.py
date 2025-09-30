# Frontend/modules/core/app_setup.py (mit shared_state)

import gevent
import logging
import requests
import logging
import sys
import platform
import os

from .config_loader_frontend import load_and_parse_config_frontend
from .utils_frontend import setup_logger
from config_frontend import DEBUG, SERVER_ADDRESS

# Importiere das neue shared_state Modul
from . import shared_state_frontend as g

#---------------------------------

def start_darts_client():
    """
    Stellt in einer robusten Schleife die initiale Verbindung zum Backend her.
    Diese Funktion läuft nur einmal beim Start des Frontends und gibt nicht auf.
    """
    backend_url = f'wss://{g.SERVER_ADDRESS}'
    api_url = f"https://{g.SERVER_ADDRESS}/api/supported-modes"
    connect_options = {
        'transports': ['websocket'],
        'socketio_path': '/api/socket.io/',
        'headers': {'User-Agent': 'Himues-Autodarts-Scoreboard'}
    }

    while True:
        try:
            # Versucht nur zu verbinden, wenn noch keine Verbindung besteht.
            if not g.sio_client.connected:
                logging.info(f"Versuche, initiale Verbindung zum Backend herzustellen: {backend_url}")
                g.sio_client.connect(backend_url, **connect_options)
            # Wenn die Verbindung erfolgreich war, holen wir die Spielmodi
            logging.info("Verbindung erfolgreich. Rufe unterstützte Spielmodi ab...")
            response = requests.get(api_url, verify=False, timeout=5)
            response.raise_for_status()
            
            # Die Spielmodi werden geholt
            game_modes = response.json()
            g.SUPPORTED_GAME_VARIANTS.clear()
            g.SUPPORTED_GAME_VARIANTS.extend(game_modes)
            
            # Sende das neue Event mit den Spielmodi an alle Browser
            g.socketio_server.emit('backend_connected', {'modes': game_modes})

            # Jetzt wird das Banner mit den korrekten Daten ausgegeben
            is_gunicorn = "gunicorn" in sys.argv[0]
            gunicorn_msg = 'RUNNING MODE: Gunicorn' if is_gunicorn else 'RUNNING MODE: Direct execution'

            banner_message = f"""

##################################################
        WELCOME TO HIMUES-Scoreboard-Frontend
##################################################
VERSION: {g.VERSION or "nicht gesetzt"}
RUNNING OS: {platform.system()} | {os.name} | {platform.release()}
SUPPORTED GAME-VARIANTS: {", ".join(g.SUPPORTED_GAME_VARIANTS)}

{gunicorn_msg}
"""
            logging.info(banner_message)
            break 
            
        except Exception as e:
            logging.error(f"Initiale Verbindung fehlgeschlagen: {e}")
            logging.info("Nächster Versuch in 3 Sekunden...")
            gevent.sleep(3)

#---------------------------------

def initialize_application():
    """Bündelt die Initialisierungslogik."""
    load_and_parse_config_frontend()
    setup_logger()
    # Startet den Verbindungsversuch als Hintergrund-Task, damit der Server starten kann.
    g.socketio_server.start_background_task(target=start_darts_client)
