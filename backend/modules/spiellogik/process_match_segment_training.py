# Backend/modules/spiellogik/process_match_segment_training.py

import logging
from dataclasses import dataclass
from ..core import shared_state as g
from ..core import constants as c
from ..core.utils_backend import log_function_call
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event
from ..database.database_handler import get_db_connection, get_player_data_from_db, create_guest_player, save_leg_to_history, calculate_and_update_guest_average


@dataclass
class TargetInfo:
    """Bündelt die Informationen zum aktuellen Ziel im Segment Training."""
    segment: str = "" # Das zu treffende Segment als Zahl (z.B. "20") oder "Bull".
    mode:    str = "" # Der genaue Bereich des Segments (z.B. "Triple", "Outer Single").

@log_function_call
def process_match_segment_training(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Segment Training'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit den trainingsspezifischen Daten:
    1. Erstellt das korrekte MatchInfo-Objekt mit den Endbedingungen.
    2. Erstellt ein spezielles TargetInfo-Objekt für das genaue Runden-Ziel.
    3. Ergänzt jedes Spielerobjekt um die Statistiken 'darts_thrown_leg',
       'leg_hit_rate' und 'match_hit_rate'.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event    = create_universal_game_event(live_game_data)

    # Segment Training-spezifische MatchInfo erstellen und zuweisen
    settings = live_game_data.get(c.KEY_SETTINGS, {})
    event.match.game_mode = "Segment Training"
    event.match.ends_after_type = c.KEY_HITS if settings.get(c.KEY_HITS) else c.KEY_DARTS
    event.match.ends_after_value = settings.get(c.KEY_HITS) or settings.get('throws')

    # Spezielles TargetInfo-Objekt für das Runden-Ziel erstellen
    target_data = live_game_data.get(c.KEY_STATE, {}).get(c.KEY_TARGET, {})

    event.turn.target = TargetInfo(
        segment = target_data.get("number"),
        mode    = target_data.get("bed")
    )

    # Spielerobjekte mit trainingsspezifischen Statistiken anreichern
    stats_list = live_game_data.get(c.KEY_STATS, [])

    # KORREKTE SCHLEIFE: Wir verwenden enumerate, um den Index `i` zu erhalten.
    for i, player_obj in enumerate(event.players):
        if i < len(stats_list):
            player_stats = stats_list[i]
            player_obj.darts_thrown_leg = player_stats.get(c.KEY_LEG_STATS, {}).get('dartsThrown', 0)
            player_obj.leg_hit_rate = player_stats.get(c.KEY_LEG_STATS, {}).get(c.KEY_HITRATE, 0.0)
            player_obj.match_hit_rate = player_stats.get(c.KEY_MATCH_STATS, {}).get(c.KEY_HITRATE, 0.0)

    # Überschreibe den Spielzustand, falls nötig
    # Da Segment Training immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"

    return event.to_dict()

#---#-------------------------------------------------------------

@log_function_call
def update_segment_training_statistic_after_leg(event_data):
    """
    Bündelt die Logik zur Hit-Rate-Verarbeitung am Ende eines Segment-Training-Legs.
    Enthält Schutz gegen doppeltes Speichern.
    """
    game_mode = 'segment_training'
    
    # --- SCHUTZ GEGEN DOPPELTES SPEICHERN ---
    match_id = event_data.get(c.KEY_ID)
    current_leg = event_data.get(c.KEY_LEG)
    leg_id = f"{match_id}-{current_leg}"
    
    if leg_id in g.processed_leg_ids:
        if g.DEBUG > 0:
            logging.info(f"Leg {leg_id} wurde bereits verarbeitet. Überspringe doppeltes Speichern.")
        return
    # ----------------------------------------

    if g.DEBUG > 0:
        logging.info(f"HIT-RATE-VERARBEITUNG FÜR {game_mode.upper()} LEG {event_data.get(c.KEY_LEG)} GESTARTET")

    with get_db_connection() as conn:
        if not conn: 
            return
            
        try:
            # Gewinner des Legs ermitteln
            leg_winner_index = event_data.get(c.KEY_GAME_WINNER, -1)

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

                # Hole oder erstelle den Spieler in der 'players_segment_training' Tabelle
                player_info = get_player_data_from_db(conn, player_name, game_mode=game_mode)
                if not player_info:
                    player_db_id = create_guest_player(conn, player_name, game_mode=game_mode)
                    conn.commit()
                    if player_db_id is None: 
                        continue
                    player_info = {'id': player_db_id}

                player_db_id = player_info.get('id')
                
                # Bestimmen, ob dieser Spieler gewonnen hat
                is_winner = (i == leg_winner_index)

                # Speichere die Leg-Daten in der 'games_history_atc' Tabelle
                db_leg_stats = {'hit_rate': leg_hit_rate, 'darts': leg_darts}
                if leg_darts > 0:
                    save_leg_to_history(conn, player_db_id, match_id, current_leg, db_leg_stats, game_mode=game_mode, is_win=is_winner)

                # Berechne die neue langfristige Hit-Rate und aktualisiere die 'players_atc' Tabelle
                new_overall_hit_rate = calculate_and_update_guest_average(conn, player_db_id, game_mode=game_mode)

                # Aktualisiere den In-Memory-Cache für die sofortige Anzeige im nächsten Event
                if player_name_lower in g.player_data_map:
                    g.player_data_map[player_name_lower][c.KEY_OA_HIT_RATE] = new_overall_hit_rate
            
            conn.commit()
            
            # Nach erfolgreichem Speichern Leg als verarbeitet markieren
            g.processed_leg_ids.add(leg_id)

        except Exception as e:
            logging.error(f"Ein schwerwiegender Fehler ist bei der Hit-Rate-Verarbeitung aufgetreten: {e}")
            conn.rollback()
