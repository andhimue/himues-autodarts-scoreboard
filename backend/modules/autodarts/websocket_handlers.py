# Backend/modules/autodarts/websocket_handlers.py

import logging
import json
import requests
from requests.exceptions import RequestException
import time
import ssl
import websocket
import logging
import traceback
import gevent
import math
import urllib3
from datetime import datetime, timezone, timedelta
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Die .. bedeuten "gehe eine Verzeichnisebene nach oben"
from ..core import shared_state as g
from ..core import constants as c
from ..core import security_module
from ..core.utils_backend import log_event, log_event_ad, log_function_call, broadcast, write_json_to_file
from ..autodarts.autodarts_api_client import fetch_and_update_board_address, get_player_average

# Spiel-Module
from ..spiellogik.match_handler import orchestrate_match_start_and_finish, _request_initial_game_update

from ..spiellogik.process_match_x01 import process_match_x01, update_x01_statistic_after_leg
from ..spiellogik.process_match_cricket import process_match_cricket, update_cricket_tactics_statistic_after_leg
from ..spiellogik.process_match_bermuda import process_match_bermuda
from ..spiellogik.process_match_shanghai import process_match_shanghai
from ..spiellogik.process_match_gotcha import process_match_gotcha
from ..spiellogik.process_match_atc import process_match_atc, update_atc_statistic_after_leg
from ..spiellogik.process_match_rtw import process_match_rtw
from ..spiellogik.process_match_bull_off import process_match_bull_off
from ..spiellogik.process_match_random_checkout import process_match_random_checkout
from ..spiellogik.process_match_countup import process_match_countup, update_countup_statistic_after_leg
from ..spiellogik.process_match_segment_training import process_match_segment_training, update_segment_training_statistic_after_leg
from ..spiellogik.process_match_bobs27 import process_match_bobs27

# ============================================================================
# === Statische Dispatcher auf Modulebene sind am Ende der Datei definiert ===
# ============================================================================

def _websocket_connection_loop(cert_check_flag):
    """
    Hält die WebSocket-Verbindung in einer Endloss-Schleife aufrecht.

    Diese Funktion wird in einem eigenen Greenlet ausgeführt und versucht
    automatisch, die Verbindung zum Autodarts-Server wiederherzustellen, falls sie unterbrochen wird.

    Args:
        cert_check_flag (bool): Ein Flag, das bestimmt, ob die SSL-Zertifikate des Servers überprüft werden sollen.
    """
    while True:
        try:
            logging.info("Connecting to Autodarts WebSocket...")
            websocket_connection = websocket.WebSocketApp(
                g.AUTODARTS_WEBSOCKET_URL,
                header=security_module.get_websocket_header(),
                on_open    = on_open_autodarts,
                on_message = on_message_autodarts,
                on_error   = on_error_autodarts,
                on_close   = on_close_autodarts
            )
            sslOptions = {"cert_reqs": ssl.CERT_NONE} if not cert_check_flag else None
            
            # run_forever() ist blockierend, aber da es in einem Greenlet läuft,
            # blockiert es nicht die Hauptanwendung.
            # Führt zudem zusätzlich in regelmäßigen Abständen einen Ping aus,
            # in der Hoffnung, dass die Verbindung zum Autodarts-Server nicht wegen
            # Inaktivität abgebrochen wird.
            websocket_connection.run_forever(
                sslopt=sslOptions, 
                ping_interval=25,  # HINZUGEFÜGT: Sendet alle 25 Sekunden einen Ping
                ping_timeout=10    # HINZUGEFÜGT: Wartet maximal 10 Sekunden auf eine Pong-Antwort
            )


        except Exception as e:
            logging.error("WebSocket connection loop crashed: %s", e)
        
        # Sollte run_forever abbrechen, geht es hier weiter
        logging.info("WebSocket connection lost. Retrying in 5 seconds...")
        gevent.sleep(5)

#----------------------------------------------------
@log_function_call
def connect_autodarts(cert_check_flag):
    """
    Initialisiert die WebSocket-Verbindung zum Autodarts-Server.

    Startet die `_websocket_connection_loop` in einem Hintergrund-Greenlet,
    um die Anwendung nicht zu blockieren.

    Args:
        cert_check_flag (bool): Wird an die Verbindungsschleife
                                weitergegeben, um die SSL-Prüfung zu steuern.
    """
    # Starte die Schleife und speichere eine Referenz auf den Greenlet
    g.ws_greenlet = gevent.spawn(_websocket_connection_loop, cert_check_flag)
    
    try:
        res = requests.get(g.AUTODARTS_BOARDS_URL + g.AUTODARTS_BOARD_ID, headers=security_module.get_auth_header())

    except Exception as e:
        logging.error("Failed to get user name on initial connect: %s", e)


#----------------------------------------------------

@log_function_call
def _broadcast_board_status_update(match_event_data):
    """
    Sendet einfache Status-Updates des Boards an das Frontend.

    Übersetzt technische Board-Events (z.B. 'Takeout started') in
    benutzerfreundliche Nachrichten und sendet sie per Broadcast.

    Args:
        match_event_data (dict): Die Rohdaten des Board-Events vom Server.
    """
    status_map = {
        'Takeout started': 'Takeout Started', 'Takeout finished': 'Takeout Finished', 'Manual reset': 'Manual reset',
        'Stopped': 'Board Stopped', 'Started': 'Board Started', 'Calibration started': 'Calibration Started',
        'Calibration finished': 'Calibration Finished'
    }
    event_name = match_event_data.get(c.KEY_DATA, {}).get(c.KEY_EVENT)
    status     = status_map.get(event_name)
    if status:
        event_data = {c.KEY_EVENT: "Board Status", c.KEY_DATA: {"status": status}}
        broadcast(event_data)

        if g.DEBUG:
            logging.info('Broadcast %s', status)

        

#----------------------------------------------------

@log_function_call
def on_open_autodarts(websocket_connection):
    """
    Callback-Funktion, die bei erfolgreichem WebSocket-Verbindungsaufbau ausgeführt wird.

    Abonniert die statischen Kanäle für Board- und User-Events, um
    Benachrichtigungen über neue Matches oder Lobby-Aktivitäten zu erhalten.

    Args:
        websocket_connection: Die aktive WebSocketApp-Instanz.
    """
    # ermittle die lokale Board-Adresse
    fetch_and_update_board_address()
    
    # Es kann vorkommen, dass bei der Wiederverbindung der Autodarts-Server Daten über mehr als ein Spiel liefert die er für das aktuelle Baord
    # gefunden hat. Warum ist unklar. Möglicherweise ist da irgendwo auf dem Autodarts_Server etwas "hängengeblieben". Darum hier folgende zusätzliche Prüfungen:
    # - Werden mehrere Spiele vom Autodarts-Server zurück geliefert, nimm das neueste ohne weitere Prüfungen anhand des Datenfeldes createAt
    # - wird nur ein Spiel geliefert prüfe folgende 3 kriterien:
    #    - Prüfe ob der Match-Start (createAt) vor mehr als 2 Stunden war . So lange sollte eigentlich kein Spiel dauern
    #    - Prüfe ob die Gesamtzahl der geworfenen Darts im aktuellen Leg des Matches (das war bei den bisherigen "GeisterSpielen" so)
    #    - Prüfe ob der Status von is_finished = False ist

    try:
        res = requests.get(g.AUTODARTS_MATCHES_URL, headers=security_module.get_auth_header(), timeout=10)
        res.raise_for_status()
        all_matches = res.json()

        # 1. Filtere alle Matches heraus, die zu unserem Board gehören
        board_matches = []
        for m in all_matches:
            for p in m.get(c.KEY_PLAYERS, []):
                if 'boardId' in p and p.get('boardId') == g.AUTODARTS_BOARD_ID:
                    board_matches.append(m)
                    break 

        # 2. Wenn Spiele gefunden wurden, finde das Neueste und wende den Zeit-Filter an
        if board_matches:
            if g.DEBUG:
                logging.info(f"Potenzielle Matches gefunden: {len(board_matches)}. Prüfe das Neueste.")

            try:
                # 3. Sortiere die Matches nach 'createdAt' absteigend (neuestes zuerst)
                sorted_matches = sorted(
                    board_matches,
                    key=lambda m: datetime.fromisoformat(m['createdAt'].replace('Z', '+00:00')),
                    reverse=True
                )
                newest_match = sorted_matches[0]

                # 4. Prüfe nur dieses eine Spiel: Ist es nicht älter als das konfigurierte Zeitlimit?
                is_too_old = True
                created_at_str = newest_match.get('createdAt')
                if created_at_str:
                    created_at_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if (datetime.now(timezone.utc) - created_at_dt) < timedelta(hours=g.RECONNECT_MATCH_MAX_AGE_HOURS):
                        is_too_old = False
                
                # 5. Wenn das neueste Spiel die Kriterien erfüllt, stelle es wieder her
                if not is_too_old:
                    if g.DEBUG:
                        logging.info(f"Neuestes Match (ID: {newest_match.get('id')}) wird wiederhergestellt.")

                    orchestrate_match_start_and_finish(
                        {c.KEY_EVENT: 'start', c.KEY_ID: newest_match.get('id')},
                        websocket_connection
                    )
                else:
                    logging.info("Neuestes gefundenes Match ist zu alt. Starte im Leerlauf.")

            except (KeyError, ValueError) as e:
                logging.error(f"Fehler beim Sortieren/Prüfen der Matches: {e}. Starte im Leerlauf.")
        else:
            if g.DEBUG:
                logging.info("Keine laufenden Matches für dieses Board gefunden. Starte im Leerlauf.")

    except RequestException as e:
        logging.error('Fetching matches failed: %s', e)

    try:
        params = {"channel": c.AUTODARTS_BOARDS, "type": c.TYPE_SUBSCRIBE, "topic": g.AUTODARTS_BOARD_ID + ".matches"}
        websocket_connection.send(json.dumps(params))
        logging.info('Receiving live information for board-id: %s', g.AUTODARTS_BOARD_ID)
    except Exception as e:
        logging.error('Websocket-Conenction-Open-boards failed: %s', e)

    try:
        user_id = security_module.get_user_id()
        params = {"channel": c.AUTODARTS_USERS, "type": c.TYPE_SUBSCRIBE, "topic": user_id + ".events"}
        websocket_connection.send(json.dumps(params))
        logging.info('Receiving live information for user-id: %s\r\n', user_id)
    except Exception as e:
        logging.error('Websocket-Conenction-Open-users failed: %s', e)
            
#----------------------------------------------------

@log_function_call
def on_close_autodarts(websocket_connection, close_status_code, close_msg):
    """
    Callback-Funktion, die bei Schließen der WebSocket-Verbindung
    ausgeführt wird.

    Loggt den Grund und den Status-Code der geschlossenen Verbindung. Die
    Logik zum Wiederverbinden befindet sich in `_websocket_connection_loop`.

    Args:
        websocket_connection: Die geschlossene WebSocketApp-Instanz.
        close_status_code (int): Der Status-Code des Schließvorgangs.
        close_msg (str): Die mitgesendete Nachricht zum Schließgrund.
    """
    logging.info(
        'Websocket [%s] closed! Status: %s, Message: %s',
        websocket_connection.url,
        close_status_code,
        close_msg
    )        
#----------------------------------------------------

@log_function_call
def on_error_autodarts(websocket_connection, error):
    """
    Callback-Funktion, die bei einem WebSocket-Fehler ausgeführt wird.

    Loggt den aufgetretenen Fehler.

    Args:
        websocket_connection: Die WebSocketApp-Instanz, bei der der Fehler auftrat.
        error (Exception):    Das aufgetretene Fehlerobjekt.
    """
    try:
        logging.error('Websocket-Conenction-Error: %s', error)

    except Exception as e:
        logging.error('Websocket-Conenction-Error logging failed: %s', e)

#----------------------------------------------------

@log_function_call
def on_message_autodarts(websocket_connection, message):
    """
    Zentraler Einstiegspunkt für alle Nachrichten vom Autodarts-Server.

    Diese Funktion analysiert den Kanal der eingehenden Nachricht und leitet
    sie an den zuständigen Handler (z.B. `_handle_matches_channel`) weiter.
    Zusätzlich werden alle Nachrichten für Debugging-Zwecke protokolliert.

    Args:
        websocket_connection: Die aktive WebSocketApp-Instanz.
        message (str): Die empfangene Nachricht als JSON-String.
    """
    with g.game_data_lock:
        try:
            m = json.loads(message)

            # JEDE eingehende Nachricht vom Autodarts-Server im Live-Log speichern
            # Initialisiere den Log, falls er noch nicht existiert
            if not hasattr(g, 'autodarts_raw_log'):
                g.autodarts_raw_log = []
            
            # Füge die neue Nachricht mit einem Zeitstempel hinzu
            log_entry = {
                "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "data": message
            }

            g.autodarts_raw_log.append(log_entry)
            
            # Sende die neue Nachricht an alle verbundenen /debugadall-Clients
            if g.socketio:
                g.socketio.emit('new_message', log_entry, namespace='/debugadall')

            # -----------------------------------------------

            channel = m.get('channel')
            event   = m.get(c.KEY_DATA, {}).get(c.KEY_EVENT)

            #g.ad_debug_log löschen, wenn die Lobby aufgerufen wird
            if m.get('channel') == c.AUTODARTS_USERS and event == "lobby-enter":    
                g.ad_debug_log.clear()
                log_event_ad('clear_log')

                #und das ganze für /debug
                g.debug_log.clear()
                log_event('clear_log')

            # BLOCK FÜR /debugad
            # Füge die Nachricht zur Liste hinzu
            g.ad_debug_log.append(m)
            if g.socketio:
                # Sende nur das letzte Update an die Live-Ansicht
                log_event_ad('ad_data_update', m)


            # Den passenden Handler aus dem statischen Dictionary holen
            handler = CHANNEL_HANDLERS.get(channel)
            if handler:
                handler(m, websocket_connection)

        except Exception as e:
#            logging.error('Websocket-Conenction-Message failed: %s', e)
            # --- HIER IST DIE ÄNDERUNG ---
            # Wir formatieren den kompletten Traceback in einen String
            tb_str = traceback.format_exc()
            
            # Und geben ihn im Fehlerlog aus
            logging.error(f"Websocket-Conenction-Message failed:\n{tb_str}")
            if g.DEBUG > 0:
                # Wir formatieren den kompletten Traceback in einen String
                tb_str = traceback.format_exc()
                
                # Und geben ihn im Fehlerlog aus
                logging.error(f"Websocket-Conenction-Message failed:\n{tb_str}")

#----------------------------------------------------
# Hilfsfunktionen für on_message_autodarts
#----------------------------------------------------
@log_function_call
def _handle_matches_channel(match_event_data, websocket_connection):
    """
    Verarbeitet Live-Spieldaten vom 'autodarts.matches'-Kanal.

    Dies ist die Hauptfunktion für die Verarbeitung von Wurf-Daten während
    eines laufenden Spiels. Sie identifiziert den Spielmodus und delegiert
    die Daten an die spezifische Verarbeitungslogik (z.B. `process_match_x01`).

    Args:
        match_event_data (dict): Die geparsten JSON-Daten der Nachricht.
        websocket_connection:    Die aktive WebSocketApp-Instanz.
    """
    data = match_event_data.get(c.KEY_DATA, {})
    
    turns_data = data.get(c.KEY_TURNS, [])

    if turns_data:
        turns_data[0].pop(c.KEY_ID, None)
        turns_data[0].pop("createdAt", None)

    if g.last_websocket_message != data and g.active_match_id and data.get(c.KEY_ID) == g.active_match_id:
        g.last_websocket_message = data
        variant = data.get(c.KEY_VARIANT)

        # Den Dispatcher nutzen um die passende Funktion zur Spielvariante aus dem Dictionary GAME_PROCESSORS zu ermitteln
        processor = GAME_PROCESSORS.get(variant)

        if processor:
            
            # Schritt 1: Prüfen, ob das Leg beendet ist, um die Statistiken zu speichern.
            if data.get(c.STATE_GAME_FINISHED):
                # Finde die passende Speicherfunktion im neuen Dispatcher
                saver_function = LEG_END_HANDLERS.get(variant)
                if saver_function:
                    # Führe die gefundene Funktion aus, um die DB zu schreiben und den Cache zu aktualisieren
                    saver_function(data)
                
                # Nach dem Speichern und der Cache-Aktualisierung wird das Event
                # nur EINMAL erstellt, aber mit den NEUEN, korrigierten Werten
                event_to_broadcast = processor(data)
                broadcast(event_to_broadcast)

            else:
                # Schritt 2: Normale Wurf-Verarbeitung (Leg läuft noch)
                event_to_broadcast = processor(data)
                broadcast(event_to_broadcast)

        else:
            logging.info(f"WARNUNG: Unbekannter Spielmodus '%s' empfangen. Keine Aktion ausgeführt.", variant)

#----------------------------------------------------

@log_function_call
def _handle_boards_channel(match_event_data, websocket_connection):
    """
    Verarbeitet Events vom 'autodarts.boards'-Kanal.

    Behandelt hauptsächlich Match-Start- und Match-Ende-Events, um die
    dynamischen Abonnements für spezifische Match-IDs zu verwalten.

    Args:
        match_event_data (dict): Die geparsten JSON-Daten der Nachricht.
        websocket_connection:    Die aktive WebSocketApp-Instanz.
    """
    data  = match_event_data.get(c.KEY_DATA, {})
    event = data.get(c.KEY_EVENT)
    
    if event in ['Manual reset', 'Started', 'Stopped', 'Takeout started', 'Takeout finished', 'Calibration started', 'Calibration finished']:
        _broadcast_board_status_update(match_event_data)
    
    orchestrate_match_start_and_finish(data, websocket_connection)

#----------------------------------------------------

@log_function_call
def _handle_users_channel(match_event_data, websocket_connection):
    """
    Verarbeitet Events vom 'autodarts.users'-Kanal.

    Fungiert als Dispatcher für benutzerspezifische Aktionen, wie das
    Betreten oder Verlassen einer Lobby.

    Args:
        match_event_data (dict): Die geparsten JSON-Daten der Nachricht.
        websocket_connection:    Die aktive WebSocketApp-Instanz.
    """
    data = match_event_data.get(c.KEY_DATA, {})
    handler = EVENT_HANDLERS.get(data.get(c.KEY_EVENT))

    if handler:
        handler(data, websocket_connection)
#----------------------------------------------------

@log_function_call
def _handle_lobby_enter(data, websocket_connection):
    """
    Behandelt das Betreten einer Lobby durch den Benutzer.

    Abonniert die notwendigen Kanäle für die spezifische Lobby-ID, um
    Live-Updates aus der Lobby zu erhalten.

    Args:
        data (dict):          Der 'data'-Teil der WebSocket-Nachricht.
        websocket_connection: Die aktive WebSocketApp-Instanz.
    """    
    lobby_id = data.get('body', {}).get(c.KEY_ID)

    if lobby_id:
        g.active_match_id = 'lobby:' + lobby_id

        params = {"channel": c.AUTODARTS_LOBBIES, "type": c.TYPE_SUBSCRIBE, "topic": f"{lobby_id}.state"}
        websocket_connection.send(json.dumps(params))
        params = {"channel": c.AUTODARTS_LOBBIES, "type": c.TYPE_SUBSCRIBE, "topic": f"{lobby_id}.events"}
        websocket_connection.send(json.dumps(params))
        g.lobbyPlayers = []

        if g.DEBUG:
            logging.info('Listen to lobby: %s', lobby_id)

#----------------------------------------------------

@log_function_call
def _handle_lobby_leave(data, websocket_connection):
    """
    Behandelt das Verlassen einer Lobby durch den Benutzer.

    Beendet die Abonnements für die spezifische Lobby-ID.

    Args:
        data (dict):          Der 'data'-Teil der WebSocket-Nachricht.
        websocket_connection: Die aktive WebSocketApp-Instanz.
    """
    lobby_id = data.get('body', {}).get(c.KEY_ID)

    if lobby_id:
        g.active_match_id = None

        params = {"channel": c.AUTODARTS_LOBBIES, "type": c.TYPE_UNSUBSCRIBE, "topic": f"{lobby_id}.state"}
        websocket_connection.send(json.dumps(params))
        params = {"channel": c.AUTODARTS_LOBBIES, "type": c.TYPE_UNSUBSCRIBE, "topic": f"{lobby_id}.events"}
        websocket_connection.send(json.dumps(params))
        g.lobbyPlayers = []

        if g.DEBUG:
            logging.info('Stop Listen to lobby: %s', lobby_id)

#----------------------------------------------------

@log_function_call
def _handle_lobbies_channel(match_event_data, websocket_connection):
    """
    erarbeitet Events vom 'autodarts.lobbies'-Kanal.

    Behandelt Zustandsänderungen innerhalb einer Lobby, wie das Beitreten
    oder Verlassen anderer Spieler, und informiert das Frontend darüber.

    Args:
        match_event_data (dict): Die geparsten JSON-Daten der Nachricht.
        websocket_connection:    Die aktive WebSocketApp-Instanz.
    """
    data = match_event_data.get(c.KEY_DATA, {})
    
    # Dieser Block prüft auf generelle Events wie "start", "finish", "delete"
    if c.KEY_EVENT in data:

        if data.get(c.KEY_EVENT) == 'start':
            # Leere das Rohdaten-Log
            g.autodarts_raw_log.clear()

            # Die gesamte Logik für das "start"-Event gehört hier hinein
            body = data.get('body', {})
            
        elif data.get(c.KEY_EVENT) in ['finish', 'delete']:
            lobby_id = data.get(c.KEY_ID)

            params = {"type": c.TYPE_UNSUBSCRIBE, "channel": c.AUTODARTS_LOBBIES, "topic": f"{lobby_id}.events"}
            websocket_connection.send(json.dumps(params))
            params = {"type": c.TYPE_UNSUBSCRIBE, "channel": c.AUTODARTS_LOBBIES, "topic": f"{lobby_id}.state"}
            websocket_connection.send(json.dumps(params))
            g.lobbyPlayers = []
            logging.info("Player index reset")
            g.player_data_map = {}

            if g.DEBUG:
                logging.info('Stop listening to lobby: %s', lobby_id)

    elif c.KEY_PLAYERS in data:
        me = any(p.get('boardId') == g.AUTODARTS_BOARD_ID for p in data.get(c.KEY_PLAYERS, []))

        if not me:
            lobby_id = data.get(c.KEY_ID)
            params = {"channel": c.AUTODARTS_LOBBIES, "type": c.TYPE_UNSUBSCRIBE, "topic": lobby_id + ".state"}
            websocket_connection.send(json.dumps(params))
            params = {"channel": c.AUTODARTS_LOBBIES, "type": c.TYPE_UNSUBSCRIBE, "topic": lobby_id + ".events"}
            websocket_connection.send(json.dumps(params))
            g.lobbyPlayers    = []
            g.active_match_id = None

            if g.DEBUG:
                logging.info('Stop Listen to lobby: %s', lobby_id)

            return

        current_player_ids = {p.get('userId') for p in data.get(c.KEY_PLAYERS, [])}
        lobbyPlayersLeft = [lp for lp in g.lobbyPlayers if lp.get('userId') not in current_player_ids]

        for lpl in lobbyPlayersLeft:
            g.lobbyPlayers.remove(lpl)
            player_name = str(lpl.get(c.KEY_NAME)).lower()
            broadcast({c.KEY_EVENT: c.EVT_LOBBY, "action": "player-left", c.KEY_PLAYER: player_name})

            if g.DEBUG:
                logging.info("%s left the lobby", player_name)

        for p in data.get(c.KEY_PLAYERS, []):
            player_id = p.get('userId')

        for p in data.get(c.KEY_PLAYERS, []):
            player_id = p.get('userId')

            if p.get('boardId') != g.AUTODARTS_BOARD_ID and not any(lp.get('userId') == player_id for lp in g.lobbyPlayers):
                g.lobbyPlayers.append(p)
                player_name = str(p.get(c.KEY_NAME)).lower()
                player_avg = None

                # Prüfen, ob eine player_id existiert, bevor die API aufgerufen wird
                if player_id:
                    player_avg = get_player_average(player_id)

                if player_avg is not None:
                    player_avg = str(math.ceil(player_avg))

                if g.DEBUG:
                    logging.info("%s ( %s average) joined the lobby", player_name, player_avg)
                broadcast({c.KEY_EVENT: c.EVT_LOBBY, "action": "player-joined", c.KEY_PLAYER: player_name, c.KEY_AVERAGE: player_avg})
                break

# ==============================================================================
# === Dispatcher-Konfigurationen ===
# Werden am Ende der Datei definiert, um sicherzustellen, dass alle
# referenzierten Funktionen bereits existieren.
# ==============================================================================

#----------------------------------------------------
# Ein Dispatcher-Directory definiert die für ein eine Bedingung (Spielmodus, Auodarts-Kanal) aufzurufende Funktion
# Die Definition außerhalb von Funktionen sorgt dafür, dass es nur einmal beim
# ersten Aufruf des Modules erstellt wird. Wäre es in _handle_matches_channel definiert, würde es bei jedem 
# Aufruf der Funkion neu erstellt.
# Ersetzt eine lange Kette von if/elif/else Abfragen

# Dispatcher für die WebSocket-Kanäle
CHANNEL_HANDLERS = {
    c.AUTODARTS_MATCHES: _handle_matches_channel,
    c.AUTODARTS_BOARDS:  _handle_boards_channel,
    c.AUTODARTS_USERS:   _handle_users_channel,
    c.AUTODARTS_LOBBIES: _handle_lobbies_channel
}

#----------------------------------------------------

# Dispatcher für Spielmodi
GAME_PROCESSORS = {
    'X01'             : process_match_x01,
    'Cricket'         : process_match_cricket,
    'Bermuda'         : process_match_bermuda,
    'Shanghai'        : process_match_shanghai,
    'Gotcha'          : process_match_gotcha,
    'ATC'             : process_match_atc,
    'RTW'             : process_match_rtw,
    'Random Checkout' : process_match_random_checkout,
    'Bull-off'        : process_match_bull_off,
    'CountUp'         : process_match_countup,
    'Segment Training': process_match_segment_training,
    "Bob's 27"        : process_match_bobs27
}

# Dispatcher für Events
EVENT_HANDLERS = {
    'lobby-enter': _handle_lobby_enter,
    'lobby-leave': _handle_lobby_leave
}

# Dispatcher für die Statistik-Speicherfunktionen am Leg-Ende
LEG_END_HANDLERS = {
    'X01':              update_x01_statistic_after_leg,
    'Cricket':          update_cricket_tactics_statistic_after_leg,
    'Tactics':          update_cricket_tactics_statistic_after_leg, #nutzt die gleiche Funktion wie Cricket
    'ATC':              update_atc_statistic_after_leg,
    'CountUp':          update_countup_statistic_after_leg,
    'Segment Training': update_segment_training_statistic_after_leg
}
#----------------------------------------------------
