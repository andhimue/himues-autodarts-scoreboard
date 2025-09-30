# Backend/modules/spiellogik/match_handler.py

import json
import requests
import logging
import traceback
from ..core import shared_state as g
from ..core import constants as c
from ..core import security_module
from ..core.utils_backend import (
    log_event, log_function_call, 
    broadcast, reset_checkouts_counter, write_json_to_file, log_event_ad
)
from ..core.database_handler import get_db_connection, get_player_data_from_db, STAT_CONFIG
from ..core.event_structure import GameEvent, MatchInfo, TurnInfo, PlayerInfo
from ..autodarts.local_board_client import reset_board
from ..autodarts.autodarts_api_client import request_next_player, undo_throw

# ==============================================================================
# === Kickstart-FUNKTIONEN ===
# ==============================================================================

@log_function_call
def _request_initial_game_update():
    """
    Info:
        Die Modi ATC, RTW, Random Chekout, Segment Training, enthalten Spielmodi mit Random-Elementen
        Das Problem ist, dass diese beim Matchstart vom Autodarts-Server nciht (oder teilweise nur unvollständig)
        zur Verfügung gestellt werden. Es ist nicht ganz klar warum, aber der u.a. Request an den Autodarts-Server
        sorgt dafür, dass die fehlenden Elemente bereitgestellt und über den matches-channel ein neuer status (state)
        gesendet wird, der ALLE benötigten ELemente enthält.
    """

    try:

        if g.DEBUG >0:
            logging.info("Kickstart ausführen...")

        # Baue die URL für den PATCH-Request zusammen
        url = f"{g.AUTODARTS_MATCHES_URL}{g.active_match_id}/throws"
        response = requests.patch(
            url,
            json={},
            headers=security_module.get_auth_header()
        )

        response.raise_for_status()
        
        if response.status_code == 200:

            if g.DEBUG > 0:
                logging.info("Kickstart erfolgreich (Status 200).")

    except Exception as e:
        logging.error("Fehler beim Kickstart: %s", e)
    
#----------------------------------------------------

@log_function_call
def orchestrate_match_start_and_finish(match_event_data, websocket_connection):
    """
    Verarbeitet Match-Start- und -Ende-Events vom 'autodarts.boards'-Kanal.
    Dient als Dispatcher, um das initiale Event an das zuständige Spielmodul zu delegieren.

    Args:
        match_event_data (dict): Die Event-Daten (z.B. {'event': 'start', 'id': '...'}).
        websocket_connection: Die aktive WebSocket-Verbindung.
    """
    with g.game_data_lock:
        if match_event_data.get(c.KEY_EVENT) == 'start':
            try:
                g.active_match_id = match_event_data.get(c.KEY_ID)

                if g.DEBUG:
                    logging.info('Listen to match: %s', g.active_match_id)
                
                # Dieser Aufruf ist notwendig, um die Spielerliste und deren
                # Status (Gast, registriert etc.) für die Average-Logik zu erhalten.
                res = requests.get(g.AUTODARTS_MATCHES_URL + g.active_match_id, headers=security_module.get_auth_header())
                match_data = res.json()

                # Diese Funktion lädt nun die Averages, den Spielertyp und die Inidizes für alle Spieler
                _initialize_player_data_map(match_data)
                
                # Setzt die Liste der verarbeiteten Legs für das neue Match zurück.
                g.processed_leg_ids.clear()

                reset_checkouts_counter()

                # Abonieren der Autodarts-Bhannel für das Board und die Matches
                paramsSubscribeTakeOut =       { "channel": c.AUTODARTS_BOARDS, c.KEY_TYPE: c.TYPE_SUBSCRIBE, "topic": g.AUTODARTS_BOARD_ID + ".events" }
                websocket_connection.send(json.dumps(paramsSubscribeTakeOut))
                paramsSubscribeMatchesEvents = { "channel": c.AUTODARTS_MATCHES, c.KEY_TYPE: c.TYPE_SUBSCRIBE, "topic": g.active_match_id + ".state" }
                websocket_connection.send(json.dumps(paramsSubscribeMatchesEvents))

                _request_initial_game_update()

                if g.DEBUG:
                    logging.info('Matchon')

            except Exception as e:
                logging.error('Fetching initial match-data failed: %s', e)

        elif match_event_data.get(c.KEY_EVENT) in ['finish', 'delete']:

            if g.DEBUG:
                logging.info('Stop listening to match: %s', match_event_data.get(c.KEY_ID))
                    
            g.active_match_id = None
            g.player_data_map = {}
            g.last_message_to_frontend = {}
            
            # Sendet ein leeres Event, um das Frontend zurückzusetzen
            reset_event = { c.KEY_EVENT: c.EVT_MATCH_ENDED, c.KEY_PLAYERS: [] }
            broadcast(reset_event)

#----------------------------------------------------

@log_function_call
def _initialize_player_data_map(initial_match_data):
    """
    Initialisiert den Zustand für ein neues Match. Bestimmt den Typ jedes
    Spielers (Gast, Registriert, Owner), lädt die Averages, erstellt Indizes
    und speichert alles im zentralen player_data_map Dictionary.
    """
 
    if g.DEBUG > 0:
        logging.info("Neues Match erkannt, initialisiere Spielerdaten in player_data_map...")
    
    g.player_data_map.clear()

    # Den Spielmodus für die Tabellenauswahl bestimmen
    # Dictionary-Mapping statt if/elif-Kette
    variant = initial_match_data.get(c.KEY_SETTINGS, {}).get(c.KEY_GAME_MODE, initial_match_data.get(c.KEY_VARIANT, '')).lower()

    game_mode_simple = MODE_MAP.get(variant, 'x01')
    
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True) if conn else None
        
        for p_data in initial_match_data.get(c.KEY_PLAYERS, []):
            player_name = p_data.get(c.KEY_NAME, '')

            if not player_name: continue

            # Ermittle Spielertyp
            player_type = c.PLAYER_TYPE_GUEST

            # Ein Spieler ist der Owner, wenn seine User-ID mit der Host-ID übereinstimmt
            if p_data.get('userId') and p_data.get('userId') == p_data.get('hostId'):
                player_type = c.PLAYER_TYPE_OWNER

            # Ein Spieler ist registriert, wenn er ein 'user'-Objekt hat, aber nicht der Owner ist
            elif p_data.get(c.KEY_USER) is not None:
                player_type = c.PLAYER_TYPE_REGISTERED
            
            # 1. Initialisiere alle Statistik-Felder mit 0.0
            player_stats = {
                c.KEY_OA_AVERAGE: 0.0, c.KEY_OA_MPR: 0.0,
                c.KEY_OA_HIT_RATE: 0.0, c.KEY_OA_PPR: 0.0
            }
            stat_value = 0.0


            # 2. Lade den EINEN relevanten Wert aus der DB oder vom Server
            if player_type in [c.PLAYER_TYPE_OWNER, c.PLAYER_TYPE_REGISTERED] and game_mode_simple == 'x01':
                stat_value = float(p_data.get(c.KEY_USER, {}).get(c.KEY_AVERAGE, 0.0))
            elif conn:
                player_db_info = get_player_data_from_db(cursor, player_name, game_mode=game_mode_simple)
                # Hole den Spaltennamen aus der zentralen Konfiguration
                stat_column = STAT_CONFIG[game_mode_simple]['column']
                if player_db_info and player_db_info.get(stat_column) is not None:
                    stat_value = player_db_info.get(stat_column)

            # 3. Finde den korrekten Cache-Schlüssel und setze den Wert im player_stats Dictionary
            stat_key_to_update = STAT_CONFIG[game_mode_simple]['cache_key']
            player_stats[stat_key_to_update] = stat_value
            
            # 4. Baue den finalen Eintrag zusammen
            # Erstelle zuerst das Basis-Dictionary
            player_entry = {
                c.KEY_TYPE:           player_type,
                'stable_index':       p_data.get('index'),
                'display_order':      None
            }
            # Füge dann das (jetzt korrekte) player_stats-Dictionary hinzu
            player_entry.update(player_stats)
            
            # Weise das fertige, kombinierte Dictionary der Map zu
            g.player_data_map[player_name.lower()] = player_entry

#----------------------------------------------------

def create_universal_game_event(live_game_data):
    """Erstellt ein vollständiges, generisches GameEvent-Objekt direkt aus den
    Live-Daten.

    Diese zentrale Funktion dient als "Standard-Konstruktor" für alle
    Spielmodi. Sie extrahiert alle verfügbaren Informationen aus den
    Autodarts-Daten, baut die vollständige Event-Struktur inklusive einer
    generischen MatchInfo auf, stabilisiert die Spielerreihenfolge und
    ermittelt den Gewinner nach Standardregeln. Das zurückgegebene Event-Objekt
    kann anschließend in der spezifischen process_match_*-Funktion bei Bedarf
    noch modifiziert werden.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        GameEvent: Das fertige, vollständig zusammengebaute GameEvent-Objekt.
    """
    # Initialisierung der Map, falls sie noch nicht existiert
    if not g.player_data_map:
        _initialize_player_data_map(live_game_data)

    settings = live_game_data.get(c.KEY_SETTINGS, {})

    # 1. Generische MatchInfo direkt aus den Daten erstellen
    match_info = MatchInfo(
        game_mode   = settings.get(c.KEY_GAME_MODE, live_game_data.get(c.KEY_VARIANT)),
        use_db      = g.USE_DATABASE, # Setzt das Flag basierend auf der globalen Konfig
        max_rounds  = settings.get(c.KEY_MAX_ROUNDS, 0),
        start_score = settings.get(c.KEY_BASE_SCORE, 0),
        in_mode     = settings.get(c.KEY_INMODE),
        out_mode    = settings.get(c.KEY_OUTMODE),
        legs_to_win = live_game_data.get(c.KEY_LEGS, 0),
        sets_to_win = live_game_data.get(c.KEY_SETS, 0),
    )

    # 2. Basis-TurnInfo erstellen
    turn_data = live_game_data.get(c.KEY_TURNS, [{}])[0]
    turn_info = TurnInfo(
        current_round = live_game_data.get(c.KEY_ROUND, 1),
        current_leg   = live_game_data.get(c.KEY_LEG, 1),
        current_set   = live_game_data.get(c.KEY_SET, 1),
        throws        = turn_data.get(c.STATE_THROWS, []),
        busted        = turn_data.get(c.STATE_BUSTED, False)
    )

    # 3. Basis-Spielerliste erstellen und anreichern
    all_players = []
    for i, p_data in enumerate(live_game_data.get(c.KEY_PLAYERS, [])):
        player_name = p_data.get(c.KEY_NAME, '')
        player_name_lower = player_name.lower()
        
        # GEÄNDERT: Greift nur noch auf die eine, zentrale Map zu
        player_info_from_map = g.player_data_map.get(player_name_lower, {})

        # Wenn für diesen Spieler noch keine Anzeigereihenfolge gesetzt ist,
        # nimm die aktuelle Position aus der Server-Liste als die neue, feste Reihenfolge.
        if player_info_from_map.get(c.KEY_DISPLAY_ORDER) is None:
            player_info_from_map[c.KEY_DISPLAY_ORDER] = i
            # Wichtig: Änderung direkt in der globalen Map speichern
            g.player_data_map[player_name_lower][c.KEY_DISPLAY_ORDER] = i

        stats = live_game_data.get(c.KEY_STATS, [])[i] if i < len(live_game_data.get(c.KEY_STATS, [])) else {}

        # Hole die Score-Listen. Sie könnten 'None' sein.
        game_scores_list = live_game_data.get(c.KEY_GAME_SCORES)
        scores_list      = live_game_data.get(c.KEY_SCORES)

        # Greife nur dann auf die Listen zu, wenn sie existieren und der Index gültig ist.
        player_score     = game_scores_list[i] if game_scores_list and i < len(game_scores_list) else 0
        legs_won         = scores_list[i].get(c.KEY_LEGS, 0) if scores_list and i < len(scores_list) else 0
        sets_won         = scores_list[i].get(c.KEY_SETS, 0) if scores_list and i < len(scores_list) else 0

        player = PlayerInfo(
            name=player_name,
            # GEÄNDERT: Alle Daten kommen aus der neuen Map
            player_type=player_info_from_map.get(c.KEY_TYPE, c.PLAYER_TYPE_GUEST),
            display_order=player_info_from_map.get(c.KEY_DISPLAY_ORDER),
            score=player_score,
            legs_won=legs_won,
            sets_won=sets_won,
            overall_average=player_info_from_map.get(c.KEY_OA_AVERAGE, 0.0),
            overall_mpr=player_info_from_map.get(c.KEY_OA_MPR, 0.0),
            overall_hit_rate=player_info_from_map.get(c.KEY_OA_HIT_RATE, 0.0),
            overall_ppr=player_info_from_map.get(c.KEY_OA_PPR, 0.0),
            leg_average     = stats.get(c.KEY_LEG_STATS, {}).get(c.KEY_AVERAGE, 0),
            match_average   = stats.get(c.KEY_MATCH_STATS, {}).get(c.KEY_AVERAGE, 0)
        )
        all_players.append(player)

    # 4. Aktueller Spieler-Index (bezogen auf die Server-Reihenfolge)
    current_player_index = live_game_data.get(c.KEY_PLAYER, 0)

    # 5. Standard-Gewinner-Logik
    game_state         = c.STATE_THROW
    winner_info        = {}
    final_winner_index = live_game_data.get(c.KEY_WINNER, -1)
    leg_winner_index   = live_game_data.get(c.KEY_GAME_WINNER, -1)

    # Die 'players'-Liste aus den Live-Daten des Servers, die die rotierte Reihenfolge enthält
    rotated_players = live_game_data.get(c.KEY_PLAYERS, [])

    if final_winner_index != -1:
        # Regel 2: Der 'winner'-Index bezieht sich auf den STABILEN Index
        game_state = c.STATE_MATCH_WON
        winner_name = ""
        # Korrekte Schleife für die neue, verschachtelte Struktur
        # GEÄNDERT: Greift auf die neue, zentrale Map zu
        for name, data in g.player_data_map.items():
            if data.get('stable_index') == final_winner_index:
                winner_name = name
                break
        winner_info = {c.KEY_PLAYER: winner_name, c.KEY_TYPE: "Match"}

    elif leg_winner_index != -1:
        # Regel 1: Der 'gameWinner'-Index bezieht sich auf die Position in der ROTIERTEN Liste
        game_state = c.STATE_LEG_WON

        if leg_winner_index < len(rotated_players):
            winner_name = rotated_players[leg_winner_index].get('name', '')
            winner_info = {c.KEY_PLAYER: winner_name, c.KEY_TYPE: "Leg"}

    # 6. Generischen Checkout-Guide holen
    server_guide = live_game_data.get(c.KEY_STATE, {}).get('checkoutGuide', [])

    # 7. Finales Event zusammenbauen
    event = GameEvent(
        event                = c.EVT_GAME_UPDATE,
        game_state           = game_state,
        match                = match_info,
        turn                 = turn_info,
        players              = all_players,
        current_player_index = current_player_index,
        winner_info          = winner_info,
        checkout_guide       = server_guide
    )
    
    # Wir speichern hier das zuletzt ans Frontend egsendete Event zwischen.
    # Falls ein Frontend sich neu verbindet (nach NEustart oder Verbindungsabbruch,
    # kann es den aktuellen Zustand abfragen)
    g.last_message_to_frontend = event
    return event

#----------------------------------------------------

MODE_MAP = {
    'cricket': 'cricket',
    'tactics': 'tactics',
    'atc': 'atc',
    'countup': 'countup',
    'segment training': 'segment_training'
}