# Backend/modules/spiellogik/process_match_x01.py

import logging
from ..core.utils_backend import log_function_call
from ..core import shared_state as g
from ..core import constants as c
from .match_handler import create_universal_game_event

from ..core.database_handler import (
    get_db_connection, get_player_data_from_db, create_guest_player,
    save_leg_to_history, update_and_register_player, 
    calculate_and_update_guest_average
)

@log_function_call
def process_match_x01(live_game_data):
    """Verarbeitet ein Live-Update für ein X01-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    wendet anschließend die X01-spezifische Sonderregel für "First to 1 Leg"-
    Spiele an.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und potenziell
              modifizierte `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event = create_universal_game_event(live_game_data)

    # X01-Sonderlogik: Bei "First to 1 Leg" ist ein Leg-Sieg auch ein Match-Sieg.
    is_first_to_one_leg = not event.match.legs_to_win or event.match.legs_to_win == 1

    if event.game_state == c.STATE_LEG_WON and is_first_to_one_leg and not event.match.sets_to_win:
        event.game_state = c.STATE_MATCH_WON

        if event.winner_info: # Sicherstellen, dass winner_info existiert
            event.winner_info["type"] = "Match"

    return event.to_dict()
    
#-----------------------------------------------------------------------------

@log_function_call
def update_x01_statistic_after_leg(event_data):
    """
    Bündelt die gesamte Logik zur Average-Verarbeitung am Ende eines Legs
    und verhindert doppeltes Speichern für dasselbe Leg.
    """

    match_id = event_data.get(c.KEY_ID)
    current_leg = event_data.get(c.KEY_LEG)

    # --- Mechanismus zur Verhinderung doppelter Speicherung ---
    # Der Autodasrts_Server sendet Beim Matchende sofort nach dem Gewinn des Finalen Legs ein Event, das alle Daten (inkl. des Matchgewinners) enthält.
    # Nach dem Klick auf den Finish-Button sendet er ein - bis auf den Zeitstempel - absolut identisches Event.
    # Ohne sich (in g.processed_leg_ids) zu merkjen, für welches Leg dieses Matches bereits Daten in die Datenbank geschrieben wurden, würden
    # die Daten des letzten Legs 2maö egspeichert. Einmalö zum Leg-Ende und einmal nach dem Klick auf Finish.
    leg_id = f"{match_id}-{current_leg}"
    if leg_id in g.processed_leg_ids:
        if g.DEBUG > 0:
            logging.info(f"Leg {leg_id} wurde bereits verarbeitet. Überspringe doppeltes Speichern.")
        return
    # --- Ende des Mechanismus ---

    if g.DEBUG:
        logging.info("AVERAGE-VERARBEITUNG FÜR LEG %s GESTARTET", event_data.get(c.KEY_LEG))

    with get_db_connection() as conn:
        if not conn:
            return

        cursor = conn.cursor(dictionary=True)

        try:
            match_id = event_data.get(c.KEY_ID)
            current_leg = event_data.get(c.KEY_LEG)
            board_owner_name = event_data.get('host', {}).get(c.KEY_NAME)

            if not all([match_id, current_leg, board_owner_name]):
                logging.info("FEHLER: Notwendige Daten (match_id, leg, host) im Event nicht gefunden.")
                return

            for i, player in enumerate(event_data.get(c.KEY_PLAYERS, [])):
                player_name = player.get(c.KEY_NAME)
                player_name_lower = player_name.lower()

                if not player_name or player_name.lower().startswith('test'):
                    continue

                stats_block = event_data.get(c.KEY_STATS, [])[i] if i < len(event_data.get(c.KEY_STATS, [])) else {}
                player_info = get_player_data_from_db(cursor, player_name, game_mode='x01')


                if not player_info:
                    player_db_id = create_guest_player(cursor, player_name, game_mode='x01')
                    conn.commit()
                    if player_db_id is None: continue
                    player_info = {'id': player_db_id}

                player_db_id = player_info.get('id')

                # Unterscheide zwischen Gast und registriertem Spieler
                is_registered_user = player.get(c.KEY_USER) is not None

                leg_stats = stats_block.get(c.KEY_LEG_STATS, {})
                # Stelle sicher, dass das Leg Statistiken hat, bevor du speicherst
                if leg_stats and leg_stats.get('dartsThrown', 0) > 0:
                    save_leg_to_history(cursor, player_db_id, match_id, current_leg, leg_stats, game_mode='x01')

                if is_registered_user:
                    # Der Spieler ist registriert oder der Board-Owner
                    # Hole den Average vom Server
                    server_overall_avg = player.get(c.KEY_USER, {}).get(c.KEY_AVERAGE)
                    if server_overall_avg is None:
                        server_overall_avg = stats_block.get(c.KEY_MATCH_STATS, {}).get(c.KEY_AVERAGE, 0)

                    # Aktualisiere Average und setze is_registered=1 in einem Aufruf
                    update_and_register_player(cursor, player_db_id, server_overall_avg, game_mode='x01')

                    # Aktualisiere den Cache
                    g.player_data_map[player_name_lower][c.KEY_OA_AVERAGE] = float(server_overall_avg)

                    if g.DEBUG:
                        logging.info("Gesamt-Avg: %.2f (vom Server übernommen und DB-Flag gesetzt)", float(server_overall_avg))

                else:
                    # Der Spieler ist ein Gast
                    calculated_avg = calculate_and_update_guest_average(cursor, player_db_id, game_mode='x01')
                    g.player_data_map[player_name_lower][c.KEY_OA_AVERAGE] = calculated_avg

                    if g.DEBUG:
                        logging.info("Gesamt-Avg: %.2f (aus Historie berechnet und gecached)", float(calculated_avg))

                if g.DEBUG:
                    logging.info("-------------------------------------------")

            conn.commit()

            # Nach erfolgreichem Speichern wird die Leg-ID hinzugefügt.
            g.processed_leg_ids.add(leg_id)
            
            if g.DEBUG:
                logging.info("\n== AVERAGE-VERARBEITUNG ERFOLGREICH BEENDET ==")

        except Exception as e:
            logging.info(f"Ein schwerwiegender Fehler ist bei der Average-Verarbeitung aufgetreten: {e}")
            conn.rollback()
