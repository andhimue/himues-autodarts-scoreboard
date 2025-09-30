# Backend/modules/spiellogik/process_match_countup.py

import logging
from ..core.utils_backend import log_function_call
from ..core import shared_state as g
from ..core import constants as c
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event
from ..core.database_handler import get_db_connection, get_player_data_from_db, create_guest_player, save_leg_to_history, calculate_and_update_guest_average

@log_function_call
def process_match_countup(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Count Up'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    überschreibt anschließend die generische MatchInfo mit den spezifischen
    Regeln für den Count Up-Modus (insbesondere die maximale Rundenanzahl).

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universal event object created
    event    = create_universal_game_event(live_game_data)

    # Count Up-specific MatchInfo created and assigned
    settings = live_game_data.get(c.KEY_SETTINGS, {})
    event.match = MatchInfo(
        game_mode  = "CountUp",
        max_rounds = settings.get(c.KEY_MAX_ROUNDS, 0)
    )

    # Überschreibe den Spielzustand, falls nötig
    # Da Shanghai immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"


    return event.to_dict()
    
#----------------------------------------------------------


@log_function_call
def update_countup_statistic_after_leg(event_data):
    """Bündelt die Logik zur PPR-Verarbeitung am Ende eines Count Up-Legs."""
    game_mode = 'countup'
    if g.DEBUG > 0:
        logging.info(f"PPR-VERARBEITUNG FÜR {game_mode.upper()} LEG {event_data.get(c.KEY_LEG)} GESTARTET")

    with get_db_connection() as conn:
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        try:
            match_id = event_data.get(c.KEY_ID)
            current_leg = event_data.get(c.KEY_LEG)
            for i, player in enumerate(event_data.get(c.KEY_PLAYERS, [])):
                player_name = player.get(c.KEY_NAME)
                player_name_lower = player_name.lower()
                if not player_name or player_name_lower.startswith('test'):
                    continue

                stats_block = event_data.get(c.KEY_STATS, [])[i]
                leg_stats = stats_block.get(c.KEY_LEG_STATS, {})
                
                player_info = get_player_data_from_db(cursor, player_name, game_mode=game_mode)
                if not player_info:
                    player_db_id = create_guest_player(cursor, player_name, game_mode=game_mode)
                    conn.commit()
                    if player_db_id is None: continue
                    player_info = {'id': player_db_id}

                player_db_id = player_info.get('id')

                if leg_stats.get('dartsThrown', 0) > 0:
                    save_leg_to_history(cursor, player_db_id, match_id, current_leg, leg_stats, game_mode=game_mode)

                new_ppr = calculate_and_update_guest_average(cursor, player_db_id, game_mode=game_mode)

                if player_name_lower in g.player_data_map:
                    g.player_data_map[player_name_lower][c.KEY_OA_PPR] = new_ppr
            conn.commit()
        except Exception as e:
            logging.error(f"Fehler bei PPR-Verarbeitung: {e}")
            conn.rollback()