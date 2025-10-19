# Backend/modules/autodarts/local_board_client.py

import requests
import logging
from ..core import shared_state as g
from ..core.utils_backend import log_function_call

# Hinweis: Die Funktionen in dieser Datei werden in `webserver_handler.py` verwendet,
# um auf Befehle zu reagieren, die über die Socket.IO-Schnittstelle empfangen werden.
# Sie ermöglichen die Fernsteuerung des Boards.

@log_function_call
def start_board():
    """Sendet einen Befehl an den lokalen Board Manager, um die Wurf-Erkennung zu starten."""
    try:
        if g.boardManagerAddress:
#            response = requests.put(g.boardManagerAddress + '/api/detection/start', timeout=5)
            response = requests.put(g.boardManagerAddress + '/api/start', timeout=5)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call to start board failed: %s", e)

#----------------------------------------------------

@log_function_call
def stop_board():
    """Sendet einen Befehl an den lokalen Board Manager, um die Wurf-Erkennung zu stoppen."""
    try:
        if g.boardManagerAddress:
#            response = requests.put(g.boardManagerAddress + '/api/detection/stop', timeout=5)
            response = requests.put(g.boardManagerAddress + '/api/stop', timeout=5)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call to stop board failed: %s", e)

#----------------------------------------------------

@log_function_call
def reset_board():
    """Sendet einen Befehl an den lokalen Board Manager, um das Board zurückzusetzen."""
    try:
        if g.boardManagerAddress:
            response = requests.post(g.boardManagerAddress + '/api/reset', timeout=5)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call to reset board failed: %s", e)

#----------------------------------------------------

@log_function_call
def calibrate_board(camId=None, distortion=False):
    """
    Sendet einen Befehl an den lokalen Board Manager, um die Auto-Kalibrierung zu starten.
    Kann optional für eine spezifische Kamera-ID ausgeführt werden.
    """
    try:
        if g.boardManagerAddress:
            # Baue die URL dynamisch zusammen
            if camId is not None:
                url = f"{g.boardManagerAddress}/api/config/calibration/auto/{camId}?distortion={distortion}"
            else:
                # Fallback auf den alten Endpunkt für die Remote-Kalibrierung, falls benötigt,
                # oder den allgemeinen lokalen Endpunkt.
                url = f"{g.boardManagerAddress}/api/config/calibration/auto?distortion={distortion}"

            response = requests.post(url, timeout=5)
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logging.error("API call to calibrate board failed: %s", e)

#----------------------------------------------------

@log_function_call
def restart_board():
    """Sendet einen Befehl an den lokalen Board Manager, um diesen neu zu starten."""
    try:
        if g.boardManagerAddress:
            response = requests.post(g.boardManagerAddress + '/api/restart', timeout=5)
            response.raise_for_status()
            return True
    except requests.exceptions.RequestException as e:
        logging.error("API call to restart board failed: %s", e)
    return False

#----------------------------------------------------

@log_function_call
def get_config():
    """Ruft die gesamte Konfiguration des lokalen Board Managers ab."""
    try:
        if g.boardManagerAddress:
            response = requests.get(g.boardManagerAddress + '/api/config', timeout=5)
            response.raise_for_status()
            return response.json()
            logging.info("RES: %s", res)
        else:
            logging.warning("DEBUG: get_config aufgerufen, aber g.boardManagerAddress ist None.") # DEBUG-Log
    except requests.exceptions.RequestException as e:
        logging.error("API call to get config failed: %s", e)
    return None

#----------------------------------------------------

@log_function_call
def patch_config(config_data):
    """Sendet Teil-Änderungen an die Konfiguration des lokalen Board Managers."""
    try:
        if g.boardManagerAddress:
            response = requests.patch(g.boardManagerAddress + '/api/config', json=config_data, timeout=5)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("API call to patch config failed: %s", e)
    return None

#----------------------------------------------------

@log_function_call
def get_stats():
    """Ruft Live-Statistiken (z.B. FPS) vom lokalen Board Manager ab."""
    try:
        if g.boardManagerAddress:
            response = requests.get(g.boardManagerAddress + '/api/state/stats', timeout=5)
            response.raise_for_status()
            return response.json()
        else:
            logging.warning("DEBUG: get_stats aufgerufen, aber g.boardManagerAddress ist None.") # DEBUG-Log
    except requests.exceptions.RequestException as e:
        logging.error("API call to get stats failed: %s", e)
    return None

#----------------------------------------------------

@log_function_call
def get_cams_state():
    """Fragt den Zustand der Kameras vom lokalen Board Manager ab."""
    try:
        if g.boardManagerAddress:
            response = requests.get(g.boardManagerAddress + '/api/cams/state', timeout=5)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("API call to get cams state failed: %s", e)
    return None

#----------------------------------------------------

@log_function_call
def get_cams_stats():
    """Ruft detaillierte Statistiken (inkl. FPS) für jede einzelne Kamera ab."""
    try:
        if g.boardManagerAddress:
            response = requests.get(g.boardManagerAddress + '/api/cams/stats', timeout=5)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("API call to get cams_stats failed: %s", e)
    return None