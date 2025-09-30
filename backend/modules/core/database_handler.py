# Backend/modules/core/database_handler.py

import logging
import traceback
import inspect
import mariadb
import os
import sys
from   contextlib import contextmanager
from   decimal import Decimal

from . import shared_state as g
from ..core import constants as c
from .utils_backend import log_event, log_function_call


#----------------------------------------------------

@contextmanager
@log_function_call
def get_db_connection():
    """Stellt eine Verbindung zur MariaDB-Datenbank über einen Context-Manager her.

       Die Verbindung wird bei Eintritt in den 'with'-Block aufgebaut und am Ende
       (auch bei Fehlern) automatisch wieder sicher geschlossen.

    Yields:
        mariadb.connection: Ein aktives Datenbank-Verbindungsobjekt.
        None:               Wenn der Verbindungsaufbau fehlschlägt.
    """

    # 'Hauptschalter', um die Datenbanknutzung zu steuern
    if not g.USE_DATABASE:
        yield None
        return # Beendet die Funktion hier, wenn die DB deaktiviert ist.

    conn = None
    
    try:
        DB_CONFIG = {
            'user':     g.DB_USER,
            'password': g.DB_PASSWORD,
            'host':     g.DB_HOST,
            'port':     int(g.DB_PORT) if g.DB_PORT else 3306,
            'database': g.DB_DATABASE,
        }

        conn = mariadb.connect(**DB_CONFIG)
        yield conn # 'return' wird durch 'yield' ersetzt

    except mariadb.Error as e:
        print(f"FEHLER bei der DB-Verbindung: {e}", file=sys.stderr)
        yield None

    finally:
        # Dieser Block wird IMMER ausgeführt, auch bei Fehlern
        if conn and conn.ping():
            conn.close()

#----------------------------------------------------

@log_function_call
def get_player_data_from_db(cursor, player_name, game_mode):
    """Ruft die Stammdaten eines Spielers anhand seines Namens aus der 
        spezifischen 'players'-Tabelle (X01, Cricket, Tactics) ab.

        Args:
            cursor:            Ein aktiver Datenbank-Cursor mit Dictionary-Unterstützung.
            player_name (str): Der Name des zu suchenden Spielers.

        Returns:
            dict: Ein Dictionary mit den Spalten 'id', 'is_registered' und 'average' des Spielers.
            None: Wenn kein Spieler mit diesem Namen gefunden wurde oder ein Datenbankfehler auftrat.
    """
    config = STAT_CONFIG.get(game_mode)
    if not config: return None
        
    table_name = config['player_table']
    column_name = config['column']
    
    sql = f"SELECT id, is_registered, {column_name} FROM {table_name} WHERE name = %s"

    if g.DEBUG:
        logging.info(f"KONSOLE-AUSGABE (SQL): %s (Parameter: '%s')", sql, player_name)
    try:
        cursor.execute(sql, (player_name,))
        player_data = cursor.fetchone()
        
        # Wenn Daten gefunden wurden und ein Average vorhanden ist
        if player_data and player_data.get(column_name) is not None:
            # Prüfe, ob es ein Decimal ist und wandle es in float um
            if isinstance(player_data[column_name], Decimal):
                # Wenn ja, wandle ihn sofort in einen float um.
                player_data[column_name] = float(player_data[column_name])
        
        return player_data
        
    except mariadb.Error as e:
        logging.error("DB-Fehler beim Lesen des Spielers '%s': %s", player_name, e)
        return None
        
#----------------------------------------------------

@log_function_call
def create_guest_player(cursor, player_name, game_mode):
    """Legt einen neuen Spieler als Gast (is_registered = 0) in der 
        spezisfischen 'players'-Tabelle (X01, Cricket, Tactics) an.

        Args:
            cursor:            Ein aktiver Datenbank-Cursor.
            player_name (str): Der Name des neuen Gast-Spielers.

        Returns:
            int:  Die automatisch generierte ID des neu erstellten Spielers.
            None: Wenn das Einfügen aufgrund eines Datenbankfehlers fehlschlägt.
    """
    config = STAT_CONFIG.get(game_mode)
    if not config: return None

    table_name = config['player_table']
    sql = f"INSERT INTO {table_name} (name, is_registered) VALUES (%s, 0)"

    try:
        if g.DEBUG:
            logging.info("KONSOLE-AUSGABE (SQL): %s (Parameter: '%s')",sql, player_name)
        cursor.execute(sql, (player_name,))
        if g.DEBUG:
            logging.info("==> Neuer Gast-Spieler '%s' mit ID %s wurde in der DB angelegt.", player_name, cursor.lastrowid)
        return cursor.lastrowid
    except mariadb.Error as e:
        if g.DEBUG:
            logging.error("DB-Fehler beim Anlegen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

@log_function_call
def save_leg_to_history(cursor, player_db_id, match_id, leg_number, leg_stats, game_mode):
    """Speichert die detaillierten Statistiken eines einzelnen, beendeten Legs 
        in der spezifischen 'games_history'-Tabelle.

        Args:
            cursor:             Ein aktiver Datenbank-Cursor.
            player_db_id (int): Die ID des Spielers aus der 'players'-Tabelle.
            match_id (str):     Die ID des Matches, zu dem das Leg gehört.
            leg_number (int):   Die Nummer des gespielten Legs.
            leg_stats (dict):   Ein Dictionary mit den Statistiken des Legs (erwartet 'average', 'score', 'dartsThrown').
    """
    config      = SAVE_LEG_CONFIG.get(game_mode)
    stat_config = STAT_CONFIG.get(game_mode)
    if not config or not stat_config:
        return

    history_table = stat_config['history_table']
    sql = config['sql'].format(table=history_table)
    
    # Baut das values-Tupel dynamisch anhand der Konfiguration zusammen
    values = tuple([player_db_id, match_id, leg_number] + [leg_stats.get(key, 0) for key in config['keys']])
    
    cursor.execute(sql, values)    
#----------------------------------------------------

@log_function_call
def calculate_and_update_guest_average(cursor, player_db_id, game_mode):
    """Berechnet den Gesamt-Durchschnitt (Average, MPR oder Hit-Rate) für einen Gast-Spieler."""
    handler = CALCULATION_HANDLERS.get(game_mode)
    if handler:
        return handler(cursor, player_db_id, game_mode)
    return 0.0
            
#----------------------------------------------------

# Ersetzt die alten update_registered_player_average und set_player_as_registered Funktionen.
@log_function_call
def update_and_register_player(cursor, player_db_id, server_stat, game_mode):
    """Aktualisiert den Gesamt-Average eines Spielers in der 'players'-Tabelle 
        und setzt gleichzeitig sein 'is_registered'-Flag auf 1.

        Diese Funktion wird für registrierte Spieler oder den Board-Owner 
        verwendet, deren Average vom Autodarts-Server bezogen wird.

        Args:
            cursor:                 Ein aktiver Datenbank-Cursor.
            player_db_id (int):     Die ID des zu aktualisierenden Spielers.
            server_average (float): Der vom Autodarts-Server gelieferte Gesamt-Average.
    """
    config = STAT_CONFIG.get(game_mode)
    if not config:
        return

    table_name = config['player_table']
    column_name = config['column']
    
    sql = f"UPDATE {table_name} SET {column_name} = %s, is_registered = 1 WHERE id = %s"
    cursor.execute(sql, (server_stat, player_db_id))
    
    if g.DEBUG:
        logging.info("(SQL): %s (Parameter: %.2f, %s)", sql_update, new_average, player_db_id)


#----------------------------------------------------

# --- NEU: Helper-Funktionen und Dispatcher für die Berechnungslogik ---

# X01

def _calculate_x01_logic(cursor, player_db_id, game_mode):
    """
    Berechnet den langfristigen X01-Average eines Gast-Spielers.

    BERECHNUNGS-LOGIK:
    1.  Greift auf die `games_history_x01`-Tabelle zu.
    2.  Holt die Summe der Punkte (`leg_points`) und die Summe der Darts (`leg_darts`)
        der letzten 100 gespielten Legs für den Spieler.
    3.  Wendet die Standard-Average-Formel an: (Punkte / Darts) * 3.
    4.  Aktualisiert den neuen Wert in der `players_x01`-Tabelle.
    5.  Gibt den berechneten Average als float zurück.
    """
    config = STAT_CONFIG[game_mode]
    player_table = config['player_table']
    history_table = config['history_table']
    
    sql_select = f"SELECT SUM(leg_points) as total_points, SUM(leg_darts) as total_darts FROM (SELECT leg_points, leg_darts FROM {history_table} WHERE player_id = %s ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    total_points = result['total_points'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        new_stat = (total_points / total_darts) * 3
    sql_update = f"UPDATE {player_table} SET average = %s WHERE id = %s"
    cursor.execute(sql_update, (new_stat, player_db_id))
    return float(new_stat)

#----------------------------------------------------
# Cricket/Tactics

def _calculate_mpr_logic(cursor, player_db_id, game_mode):
    """
    Berechnet den langfristigen MPR (Marks Per Round) jedes Spielers.
    (Es gitb keien lngrifsigen werte für Board-Owner und registrierte
     Spieler vom Autodarts-Server)

    BERECHNUNGS-LOGIK:
    1.  Greift auf die spielmodus-spezifische `games_history_*`-Tabelle zu
        (z.B. `games_history_cricket`).
    2.  Holt die Summe der Marks (`leg_marks`) und die Summe der Darts (`leg_darts`)
        der letzten 100 gespielten Legs für den Spieler.
    3.  Wendet die Standard-MPR-Formel an: (Marks * 3) / Darts.
    4.  Aktualisiert den neuen Wert in der `players_*`-Tabelle des Spielmodus.
    5.  Gibt den berechneten MPR als float zurück.
    """
    config = STAT_CONFIG[game_mode]
    player_table = config['player_table']
    history_table = config['history_table']

    sql_select = f"SELECT SUM(leg_marks) as total_marks, SUM(leg_darts) as total_darts FROM (SELECT leg_marks, leg_darts FROM {history_table} WHERE player_id = %s ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    total_marks = result['total_marks'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        new_stat = (total_marks * 3) / total_darts
    sql_update = f"UPDATE {player_table} SET mpr = %s WHERE id = %s"
    cursor.execute(sql_update, (new_stat, player_db_id))
    return float(new_stat)

#----------------------------------------------------
# Around the Clock

def _calculate_hit_rate_logic(cursor, player_db_id, game_mode):
    """
    Berechnet die langfristige Hit-Rate (%) jedes Spielers.
    (Es gitb keien lngrifsigen werte für Board-Owner und registrierte
     Spieler vom Autodarts-Server)
     
    BERECHNUNGS-LOGIK:
    1.  Greift auf die `games_history_atc`-Tabelle zu.
    2.  Holt alle `leg_hit_rate`-Werte der letzten 100 gespielten Legs.
    3.  Berechnet den mathematischen Durchschnitt (Mittelwert) dieser Hit-Rates
        direkt in der SQL-Abfrage (`AVG()`).
    4.  Aktualisiert diesen neuen Durchschnittswert in der `players_atc`-Tabelle.
    5.  Gibt die berechnete Hit-Rate als float zurück.
    """
    config = STAT_CONFIG[game_mode]
    player_table = config['player_table']
    history_table = config['history_table']

    sql_select = f"SELECT AVG(leg_hit_rate) as avg_hit_rate FROM (SELECT leg_hit_rate FROM {history_table} WHERE player_id = %s ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    new_stat = result['avg_hit_rate'] or 0.0
    sql_update = f"UPDATE {player_table} SET hit_rate = %s WHERE id = %s"
    cursor.execute(sql_update, (new_stat, player_db_id))
    return float(new_stat)

#----------------------------------------------------
# Count Up

def _calculate_ppr_logic(cursor, player_db_id, game_mode):
    """
    Berechnet den langfristigen PPR (Points Per Round) eines Gast-Spielers.

    BERECHNUNGS-LOGIK:
    1.  Greift auf die `games_history_countup`-Tabelle zu.
    2.  Holt die Summe der erzielten Punkte (`leg_points`) und die Summe der
        geworfenen Darts (`leg_darts`) der letzten 100 gespielten Legs.
    3.  Wendet die Standard-PPR-Formel an, die identisch zur Average-Formel ist:
        (Punkte / Darts) * 3.
    4.  Aktualisiert den neuen Wert in der `players_countup`-Tabelle.
    5.  Gibt den berechneten PPR als float zurück.
    """
    config = STAT_CONFIG[game_mode]
    player_table = config['player_table']
    history_table = config['history_table']

    sql_select = f"SELECT SUM(leg_points) as total_points, SUM(leg_darts) as total_darts FROM (SELECT leg_points, leg_darts FROM {history_table} WHERE player_id = %s ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    total_points = result['total_points'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        # PPR ist (Punkte / Darts) * 3
        new_stat = (total_points / total_darts) * 3
    sql_update = f"UPDATE {player_table} SET ppr = %s WHERE id = %s"
    cursor.execute(sql_update, (new_stat, player_db_id))
    return float(new_stat)

#----------------------------------------------------
# --- Konfigurations-Dictionary zur Ermittlung der korrekten Berechnungsfunktion ---
CALCULATION_HANDLERS = {
    'x01'             : _calculate_x01_logic,
    'cricket'         : _calculate_mpr_logic,
    'tactics'         : _calculate_mpr_logic,
    'atc'             : _calculate_hit_rate_logic,
    'countup'         : _calculate_ppr_logic,
    'segment_training': _calculate_hit_rate_logic # Nutzt dieselbe Logik wie ATC
}

# --- Konfigurations-Dictionary für save_leg_to_history ---
SAVE_LEG_CONFIG = {
    'x01': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_average, leg_points, leg_darts) VALUES (%s, %s, %s, %s, %s, %s)",
        'keys': ['average', 'score', 'dartsThrown']
    },
    'cricket': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_marks, leg_darts) VALUES (%s, %s, %s, %s, %s)",
        'keys': ['marks', 'darts']
    },
    'tactics': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_marks, leg_darts) VALUES (%s, %s, %s, %s, %s)",
        'keys': ['marks', 'darts']
    },
        'atc': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_hit_rate, leg_darts) VALUES (%s, %s, %s, %s, %s)",
        'keys': ['hit_rate', 'darts']
    },
    'countup': {
        'sql': "INSERT INTO {table} (player_id, match_id, leg_number, leg_points, leg_darts) VALUES (%s, %s, %s, %s, %s)",
        'keys': ['score', 'dartsThrown']
    },
        'segment_training': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_hit_rate, leg_darts) VALUES (%s, %s, %s, %s, %s)",
        'keys': ['hit_rate', 'darts']
    }

}

# Ein zentrales Konfigurations-Dictionary für alle Statistik-Typen
STAT_CONFIG = {
    'x01': {
        'player_table': 'players_x01',
        'history_table': 'games_history_x01',
        'column': 'average',
        'cache_key': c.KEY_OA_AVERAGE
    },
    'cricket': {
        'player_table': 'players_cricket',
        'history_table': 'games_history_cricket',
        'column': 'mpr',
        'cache_key': c.KEY_OA_MPR
    },
    'tactics': {
        'player_table': 'players_tactics',
        'history_table': 'games_history_tactics',
        'column': 'mpr',
        'cache_key': c.KEY_OA_MPR
    },
    'atc': {
        'player_table': 'players_atc',
        'history_table': 'games_history_atc',
        'column': 'hit_rate',
        'cache_key': c.KEY_OA_HIT_RATE
    },
    'countup': {
        'player_table': 'players_countup',
        'history_table': 'games_history_countup',
        'column': 'ppr',
        'cache_key': c.KEY_OA_PPR
    },
    'segment_training': {
        'player_table': 'players_segment_training',
        'history_table': 'games_history_segment_training',
        'column': 'hit_rate',
        'cache_key': c.KEY_OA_HIT_RATE
    }
}