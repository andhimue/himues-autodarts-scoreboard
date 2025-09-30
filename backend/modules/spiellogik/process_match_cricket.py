# Backend/modules/spiellogik/process_match_cricket.py

import logging
from ..core import shared_state as g
from ..core import constants as c
from ..core.utils_backend import log_function_call
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event
from ..core.database_handler import (
    get_db_connection, get_player_data_from_db, create_guest_player,
    save_leg_to_history, calculate_and_update_guest_average
)

@log_function_call
def process_match_cricket(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Cricket'- oder 'Tactics'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    veredelt dieses anschließend mit den Cricket-spezifischen Daten:
    1. Ermittelt dynamisch die Zielsegmente (für Cricket oder Tactics) und
       aktualisiert das MatchInfo-Objekt.
    2. Fügt jedem Spielerobjekt in der Liste die 'mpr'-Statistik (Marks Per
       Round) und das 'hits'-Dictionary mit den Treffern pro Segment hinzu.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event     = create_universal_game_event(live_game_data)
    
    # Cricket-spezifische MatchInfo erstellen und zuweisen
    settings  = live_game_data.get(c.KEY_SETTINGS, {})
    game_mode = settings.get(c.KEY_GAME_MODE, live_game_data.get(c.KEY_VARIANT))
    
    # Ziele dynamisch aus den Live-Daten auslesen
    targets   = list(live_game_data.get(c.KEY_STATE, {}).get('segments', {}).keys())
    # Server-Wert "25" auf "bull" für das Frontend mappen
    targets   = ["bull" if t == "25" else t for t in targets]

    event.match.game_mode    = game_mode
    event.match.legs_to_win  = live_game_data.get(c.KEY_LEGS, 0)
    event.match.sets_to_win  = live_game_data.get(c.KEY_SETS, 0)
    event.match.max_rounds   = settings.get(c.KEY_MAX_ROUNDS, 0)
    event.match.scoring_mode = settings.get('scoringMode')
    event.match.targets      = targets

    # Spielerobjekte mit Cricket-spezifischen Daten (hits, mpr) anreichern
    segment_hits = live_game_data.get(c.KEY_STATE, {}).get('segments', {})
    stats_list = live_game_data.get(c.KEY_STATS, [])

    # Wir verwenden enumerate, um den Index (i) der Spieler in der rotierten Liste zu bekommen.
    # Dieser Index passt 1:1 zur Reihenfolge in stats_list und segment_hits.
    for i, player_obj in enumerate(event.players):
        # MPR-Wert hinzufügen
        if i < len(stats_list):
            player_obj.mpr = stats_list[i].get(c.KEY_LEG_STATS, {}).get('mpr', 0.0)

        # Hits-Dictionary für den Spieler aufbauen
        player_hits = {}
        for target in event.match.targets:
            segment_key = "25" if target == "bull" else target
            hits_for_segment = segment_hits.get(segment_key, [])
            
            if i < len(hits_for_segment):
                player_hits[target] = hits_for_segment[i]
            else:
                player_hits[target] = 0
        player_obj.hits = player_hits
    return event.to_dict()
    
#-------------------------------------------------------------------

@log_function_call
def update_cricket_tactics_statistic_after_leg(event_data):
    """
    Bündelt die gesamte Logik zur MPR-Verarbeitung am Ende eines Cricket/Tactics-Legs.
    
    BERECHNUNGS-LOGIK:
    1.  Extrahiert Spieler, Darts und Segmente aus dem finalen Leg-Event.
    2.  Für jeden Spieler wird die Gesamtzahl der "Marks" (Treffer) berechnet.
        -   Single = 1 Mark, Double = 2 Marks, Triple = 3 Marks.
        -   Bei "Cut Throat" werden Punkte, die bei Gegnern erzielt wurden,
            ignoriert, da sie nicht zur eigenen Leistung zählen.
        -   Eigene Punkte (nachdem ein Feld geschlossen wurde) werden in Marks umgerechnet:
            Beispiel: 3 Treffer auf die 20 (schließt das Feld) + 2 weitere Treffer auf die T20 (60 Punkte).
            Die 60 Punkte entsprechen 4 Marks (60 / 15), was zu 3 + 4 = 7 Marks auf der 20 führt.
            Diese Logik ist im Server-Datensatz bereits enthalten, wir müssen nur die Marks summieren.
    3.  Die ermittelten Werte (leg_marks, leg_darts) werden in die
        spielmodus-spezifische `games_history_*`-Tabelle geschrieben.
    4.  Anschließend wird der langfristige MPR des Spielers neu berechnet,
        indem die letzten 100 Legs aus der History-Tabelle herangezogen werden.
    5.  Der neue Gesamt-MPR wird in die `players_*`-Tabelle des Spielers geschrieben.
    """
    game_mode = event_data.get(c.KEY_SETTINGS, {}).get(c.KEY_GAME_MODE)
    if not game_mode or game_mode not in ['Cricket', 'Tactics']:
        return

    # KORREKTUR: Variable für kleingeschriebenen Modus erstellen
    game_mode_str = game_mode.lower()

    if g.DEBUG > 0:
        logging.info(f"MPR-VERARBEITUNG FÜR {game_mode.upper()} LEG {event_data.get(c.KEY_LEG)} GESTARTET")

    with get_db_connection() as conn:
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        try:
            match_id = event_data.get(c.KEY_ID)
            current_leg = event_data.get(c.KEY_LEG)
            segments_data = event_data.get(c.KEY_STATE, {}).get('segments', {})

            for i, player in enumerate(event_data.get(c.KEY_PLAYERS, [])):
                player_name = player.get(c.KEY_NAME)
                # KORREKTUR: Variable für kleingeschriebenen Namen erstellen
                player_name_lower = player_name.lower()
                if not player_name or player_name_lower.startswith('test'):
                    continue

                # Schritt 1: Extrahiere Darts
                stats_block = event_data.get(c.KEY_STATS, [])[i]
                leg_darts = stats_block.get(c.KEY_LEG_STATS, {}).get('dartsThrown', 0)

                # Schritt 2: Berechne Marks
                total_marks = 0
                for segment, hits_list in segments_data.items():
                    if i < len(hits_list):
                        total_marks += hits_list[i]
                
                # Hole oder erstelle den Spieler in der richtigen Tabelle
                # KORREKTUR: 'table_prefix' zu 'game_mode' und korrekte Variable übergeben
                player_info = get_player_data_from_db(cursor, player_name, game_mode=game_mode_str)
                if not player_info:
                    # KORREKTUR: 'table_prefix' zu 'game_mode' und korrekte Variable übergeben
                    player_db_id = create_guest_player(cursor, player_name, game_mode=game_mode_str)
                    conn.commit()
                    if player_db_id is None: continue
                    player_info = {'id': player_db_id}

                player_db_id = player_info.get('id')

                # Schritt 3: Speichere Leg in der History
                leg_stats = {'marks': total_marks, 'darts': leg_darts}
                if leg_darts > 0:
                    # KORREKTUR: 'table_prefix' zu 'game_mode' und korrekte Variable übergeben
                    save_leg_to_history(cursor, player_db_id, match_id, current_leg, leg_stats, game_mode=game_mode_str)

                # Schritt 4 & 5: Berechne und speichere neuen Gesamt-MPR
                # KORREKTUR: korrekte Variable übergeben
                new_mpr = calculate_and_update_guest_average(cursor, player_db_id, game_mode=game_mode_str)
                
                # NEU: Aktualisiere das korrekte Feld im Cache
                if player_name_lower in g.player_data_map:
                    # KORREKTUR: c.KEY_OA_MPR aus constants verwenden
                    g.player_data_map[player_name_lower][c.KEY_OA_MPR] = new_mpr

            conn.commit()
        except Exception as e:
            logging.error(f"Ein schwerwiegender Fehler ist bei der MPR-Verarbeitung aufgetreten: {e}")
            conn.rollback()