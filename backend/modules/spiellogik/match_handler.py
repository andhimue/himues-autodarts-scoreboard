# Backend/modules/spiellogik/match_handler.py

import json
import requests
import logging
from ..core import shared_state as g
from ..core import constants as c
from ..core import security_module
from ..core.utils_backend import (
    log_event, log_function_call, 
    broadcast, reset_checkouts_counter, write_json_to_file, log_event_ad
)
from ..database.database_handler import (
    get_db_connection, get_player_data_from_db, STAT_CONFIG, 
    create_guest_player, update_and_register_player
)
from ..core.event_structure import GameEvent, MatchInfo, TurnInfo, PlayerInfo

# NEU: Import für den API-Abruf
from ..autodarts.autodarts_api_client import get_player_average

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
    
    NEU: Beim Match-Ende (finish) wird der aktuelle Average vom Server geholt und gespeichert.
    """
    with g.game_data_lock:
        event_type = match_event_data.get(c.KEY_EVENT)
        match_id = match_event_data.get(c.KEY_ID)
        if event_type == 'start':
            try:
                g.active_match_id = match_id

                if g.DEBUG:
                    logging.info('Listen to match: %s', g.active_match_id)
                
                res = requests.get(g.AUTODARTS_MATCHES_URL + g.active_match_id, headers=security_module.get_auth_header())
                match_data = res.json()

                _initialize_player_data_map(match_data)
                
                g.processed_leg_ids.clear()
                reset_checkouts_counter()

                g.last_throw_cache = {}
                g.current_turn_throws = {}
                g.previous_player_index = -1
                g.current_leg_index = 0 

                paramsSubscribeTakeOut =       { "channel": c.AUTODARTS_BOARDS, c.KEY_TYPE: c.TYPE_SUBSCRIBE, "topic": g.AUTODARTS_BOARD_ID + ".events" }
                websocket_connection.send(json.dumps(paramsSubscribeTakeOut))
                paramsSubscribeMatchesEvents = { "channel": c.AUTODARTS_MATCHES, c.KEY_TYPE: c.TYPE_SUBSCRIBE, "topic": g.active_match_id + ".state" }
                websocket_connection.send(json.dumps(paramsSubscribeMatchesEvents))

                _request_initial_game_update()

                if g.DEBUG:
                    logging.info('Matchon')

            except Exception as e:
                logging.error('Fetching initial match-data failed: %s', e)

        elif event_type in ['finish', 'delete']:
            if g.active_match_id and match_id == g.active_match_id:
                if g.DEBUG:
                    logging.info('Match finished: %s. Updating Stats...', match_id)

                # --- NEU: Sync der Statistiken beim Match-Ende ---
                # Wir iterieren über alle Spieler im aktuellen Match
                try:
                    # Wir brauchen den Spielmodus für die DB-Zuordnung (z.B. 'x01' oder 'cricket')
                    # Da wir den Modus im player_data_map nicht direkt haben, nehmen wir den,
                    # der zuletzt gespielt wurde (oder 'x01' als Fallback, aber besser wäre der echte).
                    # Da wir hier keine "settings" haben, müssen wir hoffen, dass wir den Modus kennen.
                    # WORKAROUND: Wir prüfen in der player_data_map, ob wir den Modus hinterlegt haben? Nein.
                    # ABER: Wir können einfach für X01 abfragen, das ist der wichtigste Fall für Average.
                    
                    # Bessere Lösung: Wir holen uns den Modus aus dem letzten Event, falls gespeichert?
                    # Oder wir versuchen einfach, für X01 zu updaten, wenn der Spieler dort existiert.
                    
                    # Wir gehen sicherheitshalber davon aus, dass wir X01 aktualisieren wollen,
                    # da dies der Haupt-Use-Case für "Average" ist. Für Cricket wäre es MPR.
                    
                    with get_db_connection() as conn:
                        if conn:
                            for p_name, p_data in g.player_data_map.items():
                                user_id = p_data.get('user_id')
                                
                                # Nur wenn eine Autodarts-User-ID vorhanden ist (registrierter Spieler)
                                if user_id:
                                    # Hole den aktuellen Average direkt von der API
                                    # Wir fragen hier explizit nach 'x01', da dies der problematische Wert war.
                                    # Für Cricket könnte man analog 'cricket' abfragen.
                                    fresh_avg = get_player_average(user_id, variant='x01')
                                    
                                    if fresh_avg is not None:
                                        # Hole DB-ID
                                        player_db_info = get_player_data_from_db(conn, p_name, game_mode='x01')
                                        if player_db_info:
                                            p_db_id = player_db_info.get('id')
                                            # Speichere in DB
                                            update_and_register_player(conn, p_db_id, fresh_avg, game_mode='x01')
                                            if g.DEBUG:
                                                logging.info(f"Finaler Sync für {p_name}: X01 Avg auf {fresh_avg} aktualisiert.")
                            
                            conn.commit()
                except Exception as e:
                    logging.error(f"Fehler beim finalen Statistik-Sync: {e}")
                # ------------------------------------------------

                g.active_match_id = None
                g.player_data_map = {}
                g.last_message_to_frontend = {}
                
                reset_event = { c.KEY_EVENT: c.EVT_MATCH_ENDED, c.KEY_PLAYERS: [] }
                broadcast(reset_event)
            else:
                if g.DEBUG:
                    logging.info('Ignoriere finish/delete für inaktives Match ID: %s (Aktiv: %s)', match_id, g.active_match_id)

#----------------------------------------------------

@log_function_call
def _initialize_player_data_map(initial_match_data):
    """
    Initialisiert den Zustand für ein neues Match.
    NEU: Speichert 'user_id' in der Map.
    """
 
    if g.DEBUG > 0:
        logging.info("Neues Match erkannt, initialisiere Spielerdaten in player_data_map...")
    
    g.player_data_map.clear()

    variant = initial_match_data.get(c.KEY_SETTINGS, {}).get(c.KEY_GAME_MODE, initial_match_data.get(c.KEY_VARIANT, '')).lower()
    game_mode_simple = MODE_MAP.get(variant, 'x01')
    
    for p_data in initial_match_data.get(c.KEY_PLAYERS, []):
        player_name = p_data.get(c.KEY_NAME, '')
        if not player_name: continue

        player_type = c.PLAYER_TYPE_GUEST
        user_id = p_data.get('userId') # Hole die ID

        if user_id and user_id == p_data.get('hostId'):
            player_type = c.PLAYER_TYPE_OWNER
        elif p_data.get(c.KEY_USER) is not None:
            player_type = c.PLAYER_TYPE_REGISTERED
            # Fallback: Wenn userId im Top-Level fehlt, schau im 'user'-Objekt
            if not user_id:
                user_id = p_data.get(c.KEY_USER, {}).get('id')
        
        player_stats = {
            c.KEY_OA_AVERAGE: 0.0, c.KEY_OA_MPR: 0.0,
            c.KEY_OA_HIT_RATE: 0.0, c.KEY_OA_PPR: 0.0
        }
        stat_value = 0.0

        with get_db_connection() as conn:
            if conn:
                if player_type in [c.PLAYER_TYPE_OWNER, c.PLAYER_TYPE_REGISTERED] and game_mode_simple == 'x01':
                    stat_value = float(p_data.get(c.KEY_USER, {}).get(c.KEY_AVERAGE, 0.0))
                    
                    # Sofortiges Speichern des Startwerts (als Fallback)
                    try:
                        player_db_info = get_player_data_from_db(conn, player_name, game_mode='x01')
                        if not player_db_info:
                            player_db_id = create_guest_player(conn, player_name, game_mode='x01')
                            conn.commit()
                        else:
                            player_db_id = player_db_info.get('id')
                        
                        if player_db_id:
                            update_and_register_player(conn, player_db_id, stat_value, game_mode='x01')
                            conn.commit()
                    except Exception: pass # Fehler hier ignorieren, Logging wäre zu viel
                else:
                    player_db_info = get_player_data_from_db(conn, player_name, game_mode=game_mode_simple)
                    stat_column = STAT_CONFIG[game_mode_simple]['column']
                    if player_db_info and player_db_info.get(stat_column) is not None:
                        stat_value = player_db_info.get(stat_column)

        stat_key_to_update = STAT_CONFIG[game_mode_simple]['cache_key']
        player_stats[stat_key_to_update] = stat_value
        
        player_entry = {
            c.KEY_TYPE: player_type,
            'stable_index': p_data.get('index'),
            'display_order': None,
            'user_id': user_id # NEU: ID merken
        }
        player_entry.update(player_stats)
        
        g.player_data_map[player_name.lower()] = player_entry
        
#----------------------------------------------------

def create_universal_game_event(live_game_data):
    """Erstellt ein vollständiges, generisches GameEvent-Objekt direkt aus den
    Live-Daten.
    """
    # Initialisierung der Map, falls sie noch nicht existiert
    if not g.player_data_map:
        _initialize_player_data_map(live_game_data)

    # --- Leg-Wechsel Erkennung ---
    incoming_leg_index = live_game_data.get(c.KEY_LEG, 1)
    
    if g.current_leg_index != 0 and incoming_leg_index != g.current_leg_index:
        g.last_throw_cache = {}
        g.current_turn_throws = {}
        g.previous_player_index = -1 
    
    g.current_leg_index = incoming_leg_index
    # ----------------------------------

    # --- LOGIK FÜR LAST TURN DARTS CACHE ---
    current_player_idx = live_game_data.get(c.KEY_PLAYER, 0)
    raw_players = live_game_data.get(c.KEY_PLAYERS, [])
    turns_data = live_game_data.get(c.KEY_TURNS, [])
    
    if g.previous_player_index != -1 and g.previous_player_index != current_player_idx:
        if 0 <= g.previous_player_index < len(raw_players):
            prev_player_name = raw_players[g.previous_player_index].get(c.KEY_NAME)
            if prev_player_name:
                last_throws = g.current_turn_throws.get(prev_player_name, "")
                g.last_throw_cache[prev_player_name] = last_throws
                g.current_turn_throws[prev_player_name] = ""

    g.previous_player_index = current_player_idx

    if 0 <= current_player_idx < len(raw_players):
        curr_player_name = raw_players[current_player_idx].get(c.KEY_NAME)
        curr_player_id = raw_players[current_player_idx].get('id')
        current_turn_obj = next((t for t in turns_data if t.get('playerId') == curr_player_id), None)
        if current_turn_obj:
            throws = current_turn_obj.get('throws', [])
            dart_strs = []
            for t in throws:
                seg = t.get('segment', {})
                name = seg.get('name', '?')
                if name == '25': name = 'Bull'
                dart_strs.append(name)
            g.current_turn_throws[curr_player_name] = ", ".join(dart_strs)
    # ---------------------------------------

    settings = live_game_data.get(c.KEY_SETTINGS, {})

    match_info = MatchInfo(
        game_mode   = settings.get(c.KEY_GAME_MODE, live_game_data.get(c.KEY_VARIANT)),
        use_db      = g.USE_DATABASE,
        created_at  = live_game_data.get('createdAt'),
        max_rounds  = settings.get(c.KEY_MAX_ROUNDS, 0),
        start_score = settings.get(c.KEY_BASE_SCORE, 0),
        in_mode     = settings.get(c.KEY_INMODE),
        out_mode    = settings.get(c.KEY_OUTMODE),
        legs_to_win = live_game_data.get(c.KEY_LEGS, 0),
        sets_to_win = live_game_data.get(c.KEY_SETS, 0),
    )

    turn_data_raw = live_game_data.get(c.KEY_TURNS, [{}])[0]
    turn_info = TurnInfo(
        current_round = live_game_data.get(c.KEY_ROUND, 1),
        current_leg   = live_game_data.get(c.KEY_LEG, 1),
        current_set   = live_game_data.get(c.KEY_SET, 1),
        throws        = turn_data_raw.get(c.STATE_THROWS, []),
        busted        = turn_data_raw.get(c.STATE_BUSTED, False)
    )

    all_players = []
    chalkboards = live_game_data.get('chalkboards', [])
    
    for i, p_data in enumerate(live_game_data.get(c.KEY_PLAYERS, [])):
        player_name = p_data.get(c.KEY_NAME, '')
        player_name_lower = player_name.lower()
        
        player_info_from_map = g.player_data_map.get(player_name_lower, {})

        if player_info_from_map.get(c.KEY_DISPLAY_ORDER) is None:
            player_info_from_map[c.KEY_DISPLAY_ORDER] = i
            g.player_data_map[player_name_lower][c.KEY_DISPLAY_ORDER] = i

        stats = live_game_data.get(c.KEY_STATS, [])[i] if i < len(live_game_data.get(c.KEY_STATS, [])) else {}
        game_scores_list = live_game_data.get(c.KEY_GAME_SCORES)
        scores_list      = live_game_data.get(c.KEY_SCORES)

        player_score     = game_scores_list[i] if game_scores_list and i < len(game_scores_list) else 0
        legs_won         = scores_list[i].get(c.KEY_LEGS, 0) if scores_list and i < len(scores_list) else 0
        sets_won         = scores_list[i].get(c.KEY_SETS, 0) if scores_list and i < len(scores_list) else 0

        last_turn_score = None
        if i < len(chalkboards):
            rows = chalkboards[i].get('rows', [])
            if rows:
                last_entry = rows[-1]
                last_turn_score = last_entry.get('points')
        
        last_turn_darts = g.last_throw_cache.get(player_name, "")

        player = PlayerInfo(
            name=player_name,
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
            match_average   = stats.get(c.KEY_MATCH_STATS, {}).get(c.KEY_AVERAGE, 0),
            last_turn_score = last_turn_score,
            last_turn_darts = last_turn_darts
        )
        all_players.append(player)

    current_player_index = live_game_data.get(c.KEY_PLAYER, 0)
    
    game_state         = c.STATE_THROW
    winner_info        = {}
    final_winner_index = live_game_data.get(c.KEY_WINNER, -1)
    leg_winner_index   = live_game_data.get(c.KEY_GAME_WINNER, -1)
    rotated_players    = live_game_data.get(c.KEY_PLAYERS, [])

    if final_winner_index != -1:
        game_state = c.STATE_MATCH_WON
        winner_name = ""
        for name, data in g.player_data_map.items():
            if data.get('stable_index') == final_winner_index:
                winner_name = name
                break
        winner_info = {c.KEY_PLAYER: winner_name, c.KEY_TYPE: "Match"}

    elif leg_winner_index != -1:
        game_state = c.STATE_LEG_WON
        if leg_winner_index < len(rotated_players):
            winner_name = rotated_players[leg_winner_index].get('name', '')
            winner_info = {c.KEY_PLAYER: winner_name, c.KEY_TYPE: "Leg"}

    server_guide = live_game_data.get(c.KEY_STATE, {}).get('checkoutGuide', [])

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
