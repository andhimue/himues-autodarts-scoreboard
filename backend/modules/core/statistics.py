# Backend/modules/core/statistics.py

import logging
from . import shared_state as g
from ..database.database_handler import get_db_connection

def get_all_player_statistics():
    """
    Sammelt umfassende Statistiken für alle Spieler über alle Spielmodi hinweg.
    Gibt eine Liste von Dictionaries zurück.
    """
    if not g.USE_DATABASE:
        return []

    stats = {} 

    with get_db_connection() as conn:
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # --- 1. X01 Statistiken ---
        try:
            # A) Hole Grunddaten aller Spieler
            cursor.execute("SELECT id, name, average, is_registered FROM players_x01")
            players = cursor.fetchall()
            
            player_map = {} 
            
            # Temp-Speicher für die Berechnung des lokalen Averages (Last 100)
            # Key: player_id, Value: Liste von (pts, darts)
            local_leg_storage = {}

            for p in players:
                p_id = p[0]
                name = p[1]
                avg = p[2]
                is_reg = p[3]
                
                player_map[p_id] = name
                local_leg_storage[p_id] = [] # Leere Liste initialisieren
                
                if name not in stats:
                    stats[name] = {'name': name, 'x01': {}, 'cricket': {}, 'tactics': {}}
                
                stats[name]['is_registered'] = bool(is_reg) 
                stats[name]['x01']['ppr'] = float(avg) if avg else 0.0
                stats[name]['x01']['local_ppr'] = 0.0 
                stats[name]['x01']['legs_played'] = 0
                stats[name]['x01']['legs_won'] = 0
                stats[name]['x01']['matches_played'] = 0 
                stats[name]['x01']['matches_won'] = 0 

            # C) Hole ALLE Leg-Daten
            # WICHTIG: Sortiert nach Datum absteigend, damit wir die neuesten 100 einfach abschneiden können
            sql_legs = "SELECT match_id, player_id, is_win, leg_points, leg_darts FROM games_history_x01 ORDER BY finished_at DESC"
            cursor.execute(sql_legs)
            
            all_legs = cursor.fetchall()

            # D) Daten aggregieren
            matches_analysis = {}

            for row in all_legs:
                m_id = row[0]
                p_id = row[1]
                is_win = row[2]
                l_pts = row[3] 
                l_darts = row[4] 

                if p_id not in player_map: continue
                name = player_map[p_id]

                # Zähler für Gesamt-Statistik (ALLE Spiele zählen, nicht nur 100)
                stats[name]['x01']['legs_played'] += 1
                if is_win:
                    stats[name]['x01']['legs_won'] += 1
                
                # Daten für lokalen Average sammeln (werden später auf 100 begrenzt)
                if p_id in local_leg_storage:
                    local_leg_storage[p_id].append((l_pts, l_darts))

                # Match-Analyse
                if m_id not in matches_analysis: matches_analysis[m_id] = {}
                if p_id not in matches_analysis[m_id]: matches_analysis[m_id][p_id] = 0
                
                if is_win:
                    matches_analysis[m_id][p_id] += 1

            # E) Lokalen Average berechnen (Maximal letzte 100 Legs)
            for p_id, legs_list in local_leg_storage.items():
                if p_id in player_map:
                    name = player_map[p_id]
                    
                    # Hier begrenzen wir auf die letzten 100 Einträge
                    # Da die SQL-Abfrage DESC sortiert war, sind die ersten 100 die neuesten.
                    last_100 = legs_list[:100]
                    
                    sum_pts = sum(l[0] for l in last_100)
                    sum_darts = sum(l[1] for l in last_100)
                    
                    if sum_darts > 0:
                        local_avg = (sum_pts / sum_darts) * 3
                        stats[name]['x01']['local_ppr'] = local_avg

            # F) Match-Gewinner
            for m_id, players_scores in matches_analysis.items():
                if not players_scores: continue
                
                for p_id in players_scores:
                    if p_id in player_map:
                        w_name = player_map[p_id]
                        stats[w_name]['x01']['matches_played'] += 1

                winner_id = max(players_scores, key=players_scores.get)
                max_wins = players_scores[winner_id]
                
                winners = [pid for pid, wins in players_scores.items() if wins == max_wins]
                
                if len(winners) == 1 and max_wins > 0:
                    if winners[0] in player_map:
                        w_name = player_map[winners[0]]
                        stats[w_name]['x01']['matches_won'] += 1

        except Exception as e:
            logging.error(f"Fehler beim Abrufen der X01-Stats: {e}")


        # --- 2. Cricket Statistiken ---
        try:
            cursor.execute("SELECT id, name, mpr FROM players_cricket")
            players = cursor.fetchall()
            
            player_map_cricket = {}
            for p in players:
                p_id = p[0]
                name = p[1]
                mpr = p[2]

                player_map_cricket[p_id] = name
                
                if name not in stats:
                    stats[name] = {'name': name, 'x01': {}, 'cricket': {}, 'tactics': {}}
                    stats[name]['is_registered'] = False 
                
                stats[name]['cricket']['mpr'] = float(mpr) if mpr else 0.0
                stats[name]['cricket']['legs_played'] = 0
                stats[name]['cricket']['legs_won'] = 0
            
            cursor.execute("SELECT player_id, is_win FROM games_history_cricket")
            rows = cursor.fetchall()
            
            for row in rows:
                p_id = row[0]
                is_win = row[1]
                
                if p_id in player_map_cricket:
                    name = player_map_cricket[p_id]
                    stats[name]['cricket']['legs_played'] += 1
                    if is_win:
                        stats[name]['cricket']['legs_won'] += 1

        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Cricket-Stats: {e}")

        # --- 3. Tactics Statistiken ---
        try:
            cursor.execute("SELECT id, name, mpr FROM players_tactics")
            players = cursor.fetchall()
            
            player_map_tactics = {}
            for p in players:
                p_id = p[0]
                name = p[1]
                mpr = p[2]
                
                player_map_tactics[p_id] = name

                if name not in stats:
                    stats[name] = {'name': name, 'x01': {}, 'cricket': {}, 'tactics': {}}
                    stats[name]['is_registered'] = False
                
                stats[name]['tactics']['mpr'] = float(mpr) if mpr else 0.0
                stats[name]['tactics']['legs_played'] = 0
                stats[name]['tactics']['legs_won'] = 0
                
            cursor.execute("SELECT player_id, is_win FROM games_history_tactics")
            rows = cursor.fetchall()
            
            for row in rows:
                p_id = row[0]
                is_win = row[1]
                
                if p_id in player_map_tactics:
                    name = player_map_tactics[p_id]
                    stats[name]['tactics']['legs_played'] += 1
                    if is_win:
                        stats[name]['tactics']['legs_won'] += 1

        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Tactics-Stats: {e}")

    return list(stats.values())
