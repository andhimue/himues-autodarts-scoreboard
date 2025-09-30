# Backend/modules/spiellogik/process_match_atc.py

import logging
from ..core import shared_state as g
from ..core import constants as c
from ..core.utils_backend import log_function_call
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event
from ..core.database_handler import get_db_connection, get_player_data_from_db, create_guest_player, save_leg_to_history, calculate_and_update_guest_average

@log_function_call
def process_match_atc(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Around the Clock'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit den ATC-spezifischen Daten:
    1. Setzt die korrekte MatchInfo mit den ATC-Regeln (Reihenfolge etc.).
    2. Ergänzt jedes Spielerobjekt um die Statistiken 'leg_hit_rate',
       'match_hit_rate' und vor allem um das persönliche 'current_target'.
    3. Setzt das Runden-Ziel auf das Ziel des aktuell werfenden Spielers.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event = create_universal_game_event(live_game_data)

    # ATC-spezifische MatchInfo erstellen und zuweisen
    settings = live_game_data.get(c.KEY_SETTINGS, {})

    event.match = MatchInfo(
        game_mode       = "ATC",
        order           = settings.get(c.KEY_ORDER),
        hits_per_target = settings.get(c.KEY_HITS),
        scoring_mode    = settings.get(c.KEY_MODE)
    )

    #Spielerobjekte mit ATC-spezifischen Statistiken und Zielen anreichern
    stats_list = live_game_data.get(c.KEY_STATS, [])
    state_data = live_game_data.get(c.KEY_STATE, {})
    
    # KORREKTE SCHLEIFE: Wir verwenden enumerate, um den Index `i` zu erhalten,
    # der direkt mit der Reihenfolge der `stats_list` und `state_data` Listen übereinstimmt.
    for i, player_obj in enumerate(event.players):
        # Hit-Rates hinzufügen
        if i < len(stats_list):
            player_stats = stats_list[i]
            player_obj.leg_hit_rate = player_stats.get('legStats', {}).get('hitRate', 0.0)
            player_obj.match_hit_rate = player_stats.get('matchStats', {}).get('hitRate', 0.0)

        # Persönliches Ziel des Spielers ermitteln
        try:
            target_idx = state_data.get('currentTargets', [])[i]
            targets_for_player = state_data.get('targets', [])[i]
            target_obj = targets_for_player[target_idx]
            number = target_obj.get('number')
            player_obj.current_target = "Bull" if number == 25 else str(number)
        except (IndexError, TypeError):
            player_obj.current_target = "?"

    # 4. Runden-Ziel auf das Ziel des aktuellen Spielers setzen
    current_player = event.players[event.current_player_index]
    event.turn.target = current_player.current_target

    # Überschreibe den Spielzustand, falls nötig
    # Da Segment Training immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"

    return event.to_dict()
    
#-------------------------------------------------------------

@log_function_call
def update_atc_statistic_after_leg(event_data):
    """
    Bündelt die Logik zur Hit-Rate-Verarbeitung am Ende eines ATC-Legs.
    Extrahiert die Leg-Statistiken, speichert sie in der Datenbank und 
    berechnet die neue langfristige Hit-Rate für jeden Spieler.
    """
    game_mode = 'atc'
    if g.DEBUG > 0:
        logging.info(f"HIT-RATE-VERARBEITUNG FÜR {game_mode.upper()} LEG {event_data.get(c.KEY_LEG)} GESTARTET")

    with get_db_connection() as conn:
        if not conn: 
            return
            
        cursor = conn.cursor(dictionary=True)
        try:
            match_id = event_data.get(c.KEY_ID)
            current_leg = event_data.get(c.KEY_LEG)

            for i, player in enumerate(event_data.get(c.KEY_PLAYERS, [])):
                player_name = player.get(c.KEY_NAME)
                player_name_lower = player_name.lower()

                if not player_name or player_name_lower.startswith('test'):
                    continue

                # Extrahiere die relevanten Statistiken für dieses Leg
                stats_block = event_data.get(c.KEY_STATS, [])[i]
                leg_stats = stats_block.get(c.KEY_LEG_STATS, {})
                leg_darts = leg_stats.get('dartsThrown', 0)
                leg_hit_rate = leg_stats.get(c.KEY_HITRATE, 0.0)

                # Hole oder erstelle den Spieler in der 'players_atc' Tabelle
                player_info = get_player_data_from_db(cursor, player_name, game_mode=game_mode)
                if not player_info:
                    player_db_id = create_guest_player(cursor, player_name, game_mode=game_mode)
                    conn.commit()
                    if player_db_id is None: 
                        continue
                    player_info = {'id': player_db_id}

                player_db_id = player_info.get('id')

                # Speichere die Leg-Daten in der 'games_history_atc' Tabelle
                db_leg_stats = {'hit_rate': leg_hit_rate, 'darts': leg_darts}
                if leg_darts > 0:
                    save_leg_to_history(cursor, player_db_id, match_id, current_leg, db_leg_stats, game_mode=game_mode)

                # Berechne die neue langfristige Hit-Rate und aktualisiere die 'players_atc' Tabelle
                new_overall_hit_rate = calculate_and_update_guest_average(cursor, player_db_id, game_mode=game_mode)

                # Aktualisiere den In-Memory-Cache für die sofortige Anzeige im nächsten Event
                if player_name_lower in g.player_data_map:
                    g.player_data_map[player_name_lower][c.KEY_OA_HIT_RATE] = new_overall_hit_rate
            
            conn.commit()

        except Exception as e:
            logging.error(f"Ein schwerwiegender Fehler ist bei der Hit-Rate-Verarbeitung aufgetreten: {e}")
            conn.rollback()
