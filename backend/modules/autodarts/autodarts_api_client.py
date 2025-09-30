# Backend/modules/autodarts/autodarts_api_client.py

import requests
import logging
import math
from ..core import shared_state as g
from ..core import constants as c
from ..core import security_module
from ..core.utils_backend import log_function_call

@log_function_call
def get_player_average(user_id, variant='x01', limit='100'):
    """
    Fragt die Statistiken eines Spielers von der Autodarts-API ab.
    Wird aktuell nicht zur Average-Berechnung genutzt, aber für Lobby-Informationen.

    Args:
        user_id (str): Die ID des Users.
        variant (str): Die Spielvariante.
        limit (str): Die Anzahl der zu berücksichtigenden Spiele.
    """
    try:
        url = f"{g.AUTODARTS_USERS_URL}{user_id}/stats/{variant}?limit={limit}"
        headers = security_module.get_auth_header()
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        m = res.json()
        return m.get(c.KEY_AVERAGE, {}).get(c.KEY_AVERAGE)
    except requests.exceptions.RequestException as e:
        logging.error("API call to receive player-stats failed: %s", e)
        return None

@log_function_call
def start_match(lobbyId):
    """Sendet den Befehl zum Starten eines Matches aus einer Lobby an die Autodarts-API.

    Args:
        lobbyId (str): Die ID der Lobby, aus der das Match gestartet werden soll.
    """
    try:
        if g.active_match_id is not None:
            url = g.AUTODARTS_LOBBIES_URL + lobbyId + "/start"
            headers = security_module.get_auth_header()
            res = requests.post(url, headers=headers, timeout=5)
            res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call to start match failed: %s", e)

@log_function_call
def request_next_player():
    """Sendet den Befehl zum Weiterschalten zum nächsten Spieler an die Autodarts-API."""
    try:
        if g.active_match_id is not None:
            url = g.AUTODARTS_MATCHES_URL + g.active_match_id + "/players/next"
            headers = security_module.get_auth_header()
            response = requests.post(url, headers=headers, timeout=5)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call for next player failed: %s", e)

@log_function_call
def undo_throw():
    """Sendet den Befehl zum Rückgängigmachen des letzten Wurfs an die Autodarts-API."""
    try:
        if g.active_match_id is not None:
            url = g.AUTODARTS_MATCHES_URL + g.active_match_id + "/undo"
            headers = security_module.get_auth_header()
            response = requests.post(url, headers=headers, timeout=5)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call to undo throw failed: %s", e)

@log_function_call
def correct_throw(throw_indices, score):
    """Sendet einen Korrektur-Befehl für einen oder mehrere Würfe an die Autodarts-API.

    Args:
        throw_indices (list): Eine Liste von Strings, die die Indizes der zu korrigierenden
                              Würfe enthalten (z.B. ['0', '1']).
        score (str): Der Name des Segments, das als Korrekturwert gesendet werden
                     soll (z.B. "T20").
    """
    # ... (Inhalt der Funktion unverändert) ...
    try:
        data = {"changes": {}}
        for ti in throw_indices:
            data["changes"][ti] = {"point": score, "type": "normal"}
        
        # ... (Rest der Funktion unverändert) ...
    except requests.exceptions.RequestException as e:
        # ... (Rest der Funktion unverändert) ...
        logging.error("API call for correcting throw failed: %s", e)

@log_function_call
def next_game():
    """Sendet den Befehl zum Starten des nächsten Legs oder Sets an die Autodarts-API."""
    try:
        if g.active_match_id is not None:
            url = g.AUTODARTS_MATCHES_URL + g.active_match_id + "/games/next"
            headers = security_module.get_auth_header()
            response = requests.post(url, headers=headers, timeout=5)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("API call for next game failed: %s", e)

@log_function_call
def fetch_and_update_board_address():
    """Fragt die Autodarts-API nach der lokalen IP-Adresse des Board Managers."""
    try:
        if g.boardManagerAddress is None:
            url = f"{g.AUTODARTS_BOARDS_URL}{g.AUTODARTS_BOARD_ID}"
            response = requests.get(url, headers=security_module.get_auth_header())
            response.raise_for_status()
            board_data = response.json()
            board_ip = board_data.get('ip')
            if board_ip:
                g.boardManagerAddress = f"{board_ip}/"
                if g.DEBUG > 0:
                    logging.info(f"Board-Manager-Adresse erfolgreich ermittelt: {g.boardManagerAddress}")
            else:
                logging.info("Board-Manager-Adresse konnte nicht ermittelt werden (keine IP in API-Antwort).")
    except Exception as e:
        g.boardManagerAddress = None
        logging.error("Fehler beim Abrufen der Board-Manager-Adresse: %s", e)