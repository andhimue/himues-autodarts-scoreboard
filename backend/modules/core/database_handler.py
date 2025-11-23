# Backend/modules/core/database_handler.py

import logging
import sqlite3
import os
import sys
from   contextlib import contextmanager
from   decimal import Decimal
from   pathlib import Path # Importiere Path

from . import shared_state as g
from ..core import constants as c
from .utils_backend import log_event, log_function_call



# ==============================================================================
# === 1. ÖFFENTLICHE DISPATCHER-FUNKTIONEN ===
# ==============================================================================

@contextmanager
@log_function_call
def get_db_connection():
    """
    Stellt eine Datenbankverbindung über einen Context-Manager her.
    Die Entscheidung (MariaDB vs. SQLite) wird anhand von g.DATABASE_TYPE getroffen.
    
    Die Verbindung wird bei Eintritt in den 'with'-Block aufgebaut und am Ende
    (auch bei Fehlern) automatisch wieder sicher geschlossen.
    
    Yields:
        Connection: Ein aktives Datenbank-Verbindungsobjekt (mariadb.connection oder sqlite3.Connection).
        None: Wenn der Verbindungsaufbau fehlschlägt oder DB deaktiviert ist.
    """
    if not g.USE_DATABASE:
        yield None
        return
    
    db_type = g.DATABASE_TYPE
    conn = None # Connection hier initialisieren

    try:
        if db_type == 'mariadb':
            conn = _open_mariadb_connection() # NEU: Verbindung öffnen
        elif db_type == 'sqlite':
            conn = _open_sqlite_connection() # NEU: Verbindung öffnen
        else:
            logging.error("Unbekannter Datenbanktyp: %s. Verbindung nicht möglich.", db_type)
            yield None
            return # Frühzeitiger Exit bei unbekanntem Typ
            
        yield conn # Connection an den Aufrufer übergeben
    
    finally:
        # Cleanup wird von HIER aus verwaltet
        if db_type == 'mariadb' and conn and conn.ping():
            conn.close()
        elif db_type == 'sqlite' and conn:
            conn.close()

#----------------------------------------------------

@log_function_call
def get_player_data_from_db(conn, player_name, game_mode):
    """
    Ruft die Stammdaten eines Spielers anhand seines Namens aus der 
    spezifischen 'players'-Tabelle ab (DISPATCHER).

    Args:
        conn:              Die aktive Datenbank-Verbindung.
        player_name (str): Der Name des zu suchenden Spielers.
        game_mode (str):   Der Spielmodus (z.B. 'x01').

    Returns:
        dict: Ein Dictionary mit den Spalten 'id', 'is_registered' und der Statistik.
        None: Wenn kein Spieler gefunden wurde oder ein Fehler auftrat.
    """
    db_type = g.DATABASE_TYPE
    
    # Der Cursor muss hier erstellt werden, da MariaDB einen Dict-Cursor benötigt.
    if db_type == 'sqlite':
        cursor = conn.cursor() # SQLite Row Factory ist in _get_sqlite_connection gesetzt
        return _get_player_data_from_sqlite(cursor, player_name, game_mode)
    else:
        cursor = conn.cursor(dictionary=True) # MariaDB Dict-Cursor
        return _get_player_data_from_mariadb(cursor, player_name, game_mode)

#----------------------------------------------------

@log_function_call
def create_guest_player(conn, player_name, game_mode):
    """
    Legt einen neuen Spieler als Gast (is_registered = 0) in der 
    spezisfischen 'players'-Tabelle an (DISPATCHER).

    Args:
        conn:              Die aktive Datenbank-Verbindung.
        player_name (str): Der Name des neuen Gast-Spielers.
        game_mode (str):   Der Spielmodus.

    Returns:
        int:  Die automatisch generierte ID des neu erstellten Spielers.
        None: Wenn das Einfügen aufgrund eines Datenbankfehlers fehlschlägt.
    """
    db_type = g.DATABASE_TYPE
    cursor = conn.cursor() # MariaDB und SQLite verwenden einfachen Cursor für Insert/Update
    if db_type == 'sqlite':
        return _create_guest_player_sqlite(cursor, player_name, game_mode)
    else:
        return _create_guest_player_mariadb(cursor, player_name, game_mode)

#----------------------------------------------------

@log_function_call
def save_leg_to_history(conn, player_db_id, match_id, leg_number, leg_stats, game_mode, is_win=False):
    """
    Speichert die detaillierten Statistiken eines einzelnen, beendeten Legs 
    in der spezifischen 'games_history'-Tabelle (DISPATCHER).
    
    NEU: Akzeptiert den Parameter 'is_win', um den Gewinner zu markieren.

    Args:
        conn:               Die aktive Datenbank-Verbindung.
        player_db_id (int): Die ID des Spielers aus der 'players'-Tabelle.
        match_id (str):     Die ID des Matches, zu dem das Leg gehört.
        leg_number (int):   Die Nummer des gespielten Legs.
        leg_stats (dict):   Ein Dictionary mit den Statistiken des Legs.
        game_mode (str):    Der Spielmodus.
        is_win (bool):      True, wenn dieser Spieler das Leg gewonnen hat.
    """
    db_type = g.DATABASE_TYPE
    cursor = conn.cursor()
    if db_type == 'sqlite':
        _save_leg_to_history_sqlite(cursor, player_db_id, match_id, leg_number, leg_stats, game_mode, is_win)
    else:
        _save_leg_to_history_mariadb(cursor, player_db_id, match_id, leg_number, leg_stats, game_mode, is_win)
    conn.commit() # Commit für beide DBs

#----------------------------------------------------

@log_function_call
def update_and_register_player(conn, player_db_id, server_stat, game_mode):
    """
    Aktualisiert den Gesamt-Average eines Spielers in der 'players'-Tabelle 
    und setzt gleichzeitig sein 'is_registered'-Flag auf 1 (DISPATCHER).

    Args:
        conn:                   Die aktive Datenbank-Verbindung.
        player_db_id (int):     Die ID des zu aktualisierenden Spielers.
        server_stat (float):    Der vom Autodarts-Server gelieferte Gesamt-Average.
        game_mode (str):        Der Spielmodus.
    """
    db_type = g.DATABASE_TYPE
    cursor = conn.cursor()
    if db_type == 'sqlite':
        _update_and_register_player_sqlite(cursor, player_db_id, server_stat, game_mode)
    else:
        _update_and_register_player_mariadb(cursor, player_db_id, server_stat, game_mode)
    conn.commit() # Commit für beide DBs

#----------------------------------------------------

@log_function_call
def calculate_and_update_guest_average(conn, player_db_id, game_mode):
    """
    Berechnet den Gesamt-Durchschnitt (Average, MPR oder Hit-Rate) für einen Gast-Spieler.

    Args:
        conn:                   Die aktive Datenbank-Verbindung.
        player_db_id (int):     Die ID des zu berechnenden Spielers.
        game_mode (str):        Der Spielmodus.
    """
    db_type = g.DATABASE_TYPE
    
    # Der Cursor muss hier je nach DB-Typ gewählt werden
    if db_type == 'sqlite':
        cursor = conn.cursor()
    else:
        cursor = conn.cursor(dictionary=True) # MariaDB verwendet Dict-Cursor

    handler = CALCULATION_HANDLERS.get(game_mode)
    if handler:
        # Die CALCULATION_HANDLERS Logik verwendet die SQL-Abfragen
        return handler(cursor, player_db_id, game_mode)
    return 0.0

#----------------------------------------------------
# ==============================================================================
# === 2. INTERNE MARIADB IMPLEMENTIERUNGEN (Verwendet %s und mariadb.Error) ===
# ==============================================================================

def _open_mariadb_connection():
    """Öffnet die MariaDB-Verbindung und gibt das Connection-Objekt zurück (KEIN Context Manager)."""
    import mariadb

    try:
        DB_CONFIG = {
            'user':     g.DB_USER,
            'password': g.DB_PASSWORD,
            'host':     g.DB_HOST,
            'port':     int(g.DB_PORT) if g.DB_PORT else 3306,
            'database': g.DB_DATABASE,
        }
        return mariadb.connect(**DB_CONFIG)
        
    except mariadb.Error as e:
        print(f"FEHLER bei der MariaDB-Verbindung: {e}", file=sys.stderr)
        return None

#----------------------------------------------------

def _get_player_data_from_mariadb(cursor, player_name, game_mode):
    """Ruft die Stammdaten eines Spielers anhand seines Namens aus der 
        spezifischen 'players'-Tabelle (X01, Cricket, Tactics) ab."""
    config = STAT_CONFIG.get(game_mode)
    if not config: return None
        
    table_name = config['player_table']
    column_name = config['column']
    
    sql = f"SELECT id, is_registered, {column_name} FROM {table_name} WHERE name = %s" # MariaDB Platzhalter

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
        
        return player_data # Gibt Dict zurück (durch mariadb.connect(dictionary=True) im Aufrufer)
        
    except mariadb.Error as e:
        logging.error("DB-Fehler beim Lesen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

def _create_guest_player_mariadb(cursor, player_name, game_mode):
    """Legt einen neuen Spieler als Gast (is_registered = 0) in der 
        spezisfischen 'players'-Tabelle (X01, Cricket, Tactics) an."""
    config = STAT_CONFIG.get(game_mode)
    if not config: return None

    table_name = config['player_table']
    sql = f"INSERT INTO {table_name} (name, is_registered) VALUES (%s, 0)" # MariaDB Platzhalter

    try:
        if g.DEBUG:
            logging.info(f"KONSOLE-AUSGABE (SQL): %s (Parameter: '%s')",sql, player_name)
        cursor.execute(sql, (player_name,))
        if g.DEBUG:
            logging.info("==> Neuer Gast-Spieler '%s' mit ID %s wurde in der DB angelegt.", player_name, cursor.lastrowid)
        return cursor.lastrowid
    except mariadb.Error as e:
        if g.DEBUG:
            logging.error("DB-Fehler beim Anlegen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

def _save_leg_to_history_mariadb(cursor, player_db_id, match_id, leg_number, leg_stats, game_mode, is_win=False):
    """Speichert die detaillierten Statistiken eines einzelnen, beendeten Legs 
        in der spezifischen 'games_history'-Tabelle.
        NEU: Speichert auch, ob das Leg gewonnen wurde."""
    config      = SAVE_LEG_CONFIG.get(game_mode)
    stat_config = STAT_CONFIG.get(game_mode)
    if not config or not stat_config: return
        
    history_table = stat_config['history_table']
    sql = config['sql'].format(table=history_table) # Enthält %s Platzhalter
    
    # Boolean in DB-tauglichen Integer wandeln
    win_val = 1 if is_win else 0
    
    # Baut das values-Tupel dynamisch anhand der Konfiguration zusammen
    vals = [player_db_id, match_id, leg_number]
    for key in config['keys']:
        vals.append(leg_stats.get(key, 0))
    # Hänge is_win hinten an
    vals.append(win_val)
    
    values = tuple(vals)

    cursor.execute(sql, values)

#----------------------------------------------------

def _update_and_register_player_mariadb(cursor, player_db_id, server_stat, game_mode):
    """Aktualisiert den Gesamt-Average eines Spielers in der 'players'-Tabelle 
        und setzt gleichzeitig sein 'is_registered'-Flag auf 1."""
    config = STAT_CONFIG.get(game_mode)
    if not config: return

    table_name = config['player_table']
    column_name = config['column']
    
    sql = f"UPDATE {table_name} SET {column_name} = %s, is_registered = 1 WHERE id = %s" # MariaDB Platzhalter
    cursor.execute(sql, (server_stat, player_db_id))

#----------------------------------------------------
# ==============================================================================
# === 3. INTERNE SQLITE IMPLEMENTIERUNGEN (Verwendet ? und sqlite3.Error) ===
# ==============================================================================

def _initialize_sqlite_db(conn):
    """Prüft und erstellt die SQLite-Tabellenstruktur, falls nicht vorhanden."""
    logging.info("SQLite: Überprüfe und erstelle Datenbankstruktur.")
    try:
        # KORREKTUR: Versuche, das native SQLite-Schema zu laden
        sql_schema_path = Path(g.BACKEND_DIR) / "docs" / "database_schema_sqlite.sql"
        if not sql_schema_path.exists():
            # Wenn das dedizierte Schema nicht existiert, nutze das MariaDB-Schema mit minimalen Ersetzungen (Fallback)
            sql_schema_path = Path(g.BACKEND_DIR) / "docs" / "database_schema.sql"
            logging.warning("SQLite-Schema nicht gefunden, verwende MariaDB-Schema mit Ersetzungen.")
            
        
        with open(sql_schema_path, 'r') as f:
            sql_script = f.read()
            cursor = conn.cursor()
            
            # WICHTIG: Die Ersetzungen werden nur dann ausgeführt, wenn wir das MariaDB-Schema verwenden
            if sql_schema_path.name == 'database_schema.sql':
                sql_script = (
                    sql_script
                    .replace('`', '') 
                    .replace('AUTO_INCREMENT', '') 
                    .replace('ENGINE=InnoDB', '') 
                    .replace('COLLATE utf8mb4_general_ci', '')
                    .replace('ON UPDATE current_timestamp()', '')
                    .replace('varchar(255)', 'TEXT')
                    .replace('decimal(5,2)', 'REAL')
                    .replace('decimal(5,4)', 'REAL')
                    .replace('int(11)', 'INTEGER')
                    .replace('tinyint(1)', 'INTEGER')
                    .replace('timestamp', 'DATETIME')
                )
            
            # Wir verwenden nun den nativen Split des Skripts
            for statement in sql_script.split(';'):
                clean_statement = statement.strip()
                if clean_statement:
                    cursor.execute(clean_statement)
            
            conn.commit()
            logging.info("SQLite: Tabellenstruktur erfolgreich initialisiert.")
            
    except Exception as e:
        logging.error("SQLite-Tabelleninitialisierung fehlgeschlagen: %s", e)

#----------------------------------------------------

def _open_sqlite_connection():
    """Öffnet die SQLite-Verbindung und gibt das Connection-Objekt zurück (KEIN Context Manager)."""
    try:
        # Sicherstellen, dass das Verzeichnis existiert
        SQLITE_DB_DIR_LOCAL = Path(g.BACKEND_DIR) / "sqlite"
        SQLITE_DB_PATH_LOCAL = SQLITE_DB_DIR_LOCAL / "darts_scoreboard.db"

        # Sicherstellen, dass das Verzeichnis existiert
        SQLITE_DB_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
        
        db_exists = SQLITE_DB_PATH_LOCAL.exists()

        # Verbindung herstellen (erstellt die Datei, falls sie nicht existiert)
        conn = sqlite3.connect(SQLITE_DB_PATH_LOCAL)
        conn.row_factory = sqlite3.Row

        if not db_exists:
            _initialize_sqlite_db(conn)

        return conn
        
    except sqlite3.Error as e:
        print(f"FEHLER bei der SQLite-Verbindung: {e}", file=sys.stderr)
        return None

#----------------------------------------------------


def _get_player_data_from_sqlite(cursor, player_name, game_mode):
    """Ruft die Stammdaten eines Spielers anhand seines Namens aus der 
        spezifischen 'players'-Tabelle ab (verwendet Row Factory)."""
    config = STAT_CONFIG.get(game_mode)
    if not config: return None
        
    table_name = config['player_table']
    column_name = config['column']
    
    # SQLite verwendet '?' als Platzhalter
    sql = f"SELECT id, is_registered, {column_name} FROM {table_name} WHERE name = ?"

    try:
        cursor.execute(sql, (player_name,))
        player_data = cursor.fetchone() 

        if player_data:
            # Das Row-Objekt wird in ein Dict konvertiert
            result_dict = dict(player_data)
            
            # Konvertierung zu float, um mit der MariaDB-Ausgabe kompatibel zu sein
            if result_dict.get(column_name) is not None:
                result_dict[column_name] = float(result_dict[column_name])
            
            return result_dict
        
        return None
        
    except sqlite3.Error as e:
        logging.error("SQLite-Fehler beim Lesen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

def _create_guest_player_sqlite(cursor, player_name, game_mode):
    """Legt einen neuen Spieler als Gast (is_registered = 0) in der 
        spezisfischen 'players'-Tabelle an."""
    config = STAT_CONFIG.get(game_mode)
    if not config: return None

    table_name = config['player_table']
    sql = f"INSERT INTO {table_name} (name, is_registered) VALUES (?, 0)" # SQLite Platzhalter

    try:
        cursor.execute(sql, (player_name,))
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error("SQLite-Fehler beim Anlegen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

def _save_leg_to_history_sqlite(cursor, player_db_id, match_id, leg_number, leg_stats, game_mode, is_win=False):
    """Speichert die detaillierten Statistiken eines einzelnen, beendeten Legs 
        in der spezifischen 'games_history'-Tabelle."""
    config      = SAVE_LEG_CONFIG.get(game_mode)
    stat_config = STAT_CONFIG.get(game_mode)
    if not config or not stat_config: return
        
    history_table = stat_config['history_table']
    # WICHTIG: Ersetze MariaDB Platzhalter (%s) durch SQLite Platzhalter (?)
    sql = config['sql'].format(table=history_table).replace('%s', '?')
    
    win_int = 1 if is_win else 0
    
    vals = [player_db_id, match_id, leg_number]
    for key in config['keys']:
        vals.append(leg_stats.get(key, 0))
    vals.append(win_int)
    
    values = tuple(vals)
    
    cursor.execute(sql, values)

#----------------------------------------------------

def _update_and_register_player_sqlite(cursor, player_db_id, server_stat, game_mode):
    """Aktualisiert den Gesamt-Average eines Spielers in der 'players'-Tabelle 
        und setzt gleichzeitig sein 'is_registered'-Flag auf 1."""
    config = STAT_CONFIG.get(game_mode)
    if not config: return

    table_name = config['player_table']
    column_name = config['column']
    
    # NEU: SQLite-Platzhalter ist '?'
    sql = f"UPDATE {table_name} SET {column_name} = ?, is_registered = 1 WHERE id = ?"
    cursor.execute(sql, (server_stat, player_db_id))

#----------------------------------------------------
# ==============================================================================
# === 4. BERECHNUNGSLOGIK (UNVERÄNDERTE MARIADB-FUNKTIONEN) ===
# ==============================================================================

# HINWEIS: Die Logik hier wurde beibehalten. Die SQLite-Anpassung erfolgt durch Umschreiben des SQL-Strings
# innerhalb der Funktion, um die ursprüngliche Funktion als Einheit zu erhalten.

#----------------------------------------------------
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

    if g.DATABASE_TYPE == 'sqlite':
        sql_select = sql_select.replace('%s', '?') # Inline-Korrektur für SQLite
    
    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    # Der Zugriff auf result['key'] funktioniert aufgrund des MariaDB Dict-Cursors
    # oder der SQLite Row Factory.
    total_points = result['total_points'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        new_stat = (total_points / total_darts) * 3
        
    sql_update = f"UPDATE {player_table} SET average = %s WHERE id = %s"
    # Anpassung für SQLite-Syntax im Update-Statement
    if g.DATABASE_TYPE == 'sqlite':
        sql_update = sql_update.replace('%s', '?')
        cursor.execute(sql_update, (new_stat, player_db_id))
    else:
        cursor.execute(sql_update, (new_stat, player_db_id))
        
    return float(new_stat)

#----------------------------------------------------
# Cricket/Tactics
def _calculate_mpr_logic(cursor, player_db_id, game_mode):
    """
    Berechnet den langfristigen MPR (Marks Per Round) jedes Spielers.

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

    if g.DATABASE_TYPE == 'sqlite':
        sql_select = sql_select.replace('%s', '?')
        
    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    total_marks = result['total_marks'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        new_stat = (total_marks * 3) / total_darts
        
    sql_update = f"UPDATE {player_table} SET mpr = %s WHERE id = %s"
    if g.DATABASE_TYPE == 'sqlite':
        sql_update = sql_update.replace('%s', '?')
        cursor.execute(sql_update, (new_stat, player_db_id))
    else:
        cursor.execute(sql_update, (new_stat, player_db_id))
        
    return float(new_stat)

#----------------------------------------------------
# Around the Clock / Segment Training (Hit Rate)
def _calculate_hit_rate_logic(cursor, player_db_id, game_mode):
    """
    Berechnet die langfristige Hit-Rate (%) jedes Spielers.

    BERECHNUNGS-LOGIK:
    1.  Greift auf die `games_history_atc`-Tabelle zu.
    2.  Holt alle `leg_hit_rate`-Werte der letzten 100 gespielten Legs.
    3.  Berechnet den mathematischen Durchschnitt (Mittelwert) dieser Hit-Rates
        direkt in der SQL-Abfrage (`AVG()`).
    4.  Aktualisiert diesen neuen Durchschnittswert in der `players_atc`-Tabelle.
    5.  Gibt den berechneten Hit-Rate als float zurück.
    """
    config = STAT_CONFIG[game_mode]
    player_table = config['player_table']
    history_table = config['history_table']

    sql_select = f"SELECT AVG(leg_hit_rate) as avg_hit_rate FROM (SELECT leg_hit_rate FROM {history_table} WHERE player_id = %s ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    if g.DATABASE_TYPE == 'sqlite':
        sql_select = sql_select.replace('%s', '?')
        
    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    new_stat = result['avg_hit_rate'] or 0.0
    
    sql_update = f"UPDATE {player_table} SET hit_rate = %s WHERE id = %s"
    if g.DATABASE_TYPE == 'sqlite':
        sql_update = sql_update.replace('%s', '?')
        cursor.execute(sql_update, (new_stat, player_db_id))
    else:
        cursor.execute(sql_update, (new_stat, player_db_id))
        
    return float(new_stat)

#----------------------------------------------------
# Count Up (PPR)
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

    if g.DATABASE_TYPE == 'sqlite':
        sql_select = sql_select.replace('%s', '?')
        
    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    total_points = result['total_points'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        # PPR ist (Punkte / Darts) * 3
        new_stat = (total_points / total_darts) * 3
        
    sql_update = f"UPDATE {player_table} SET ppr = %s WHERE id = %s"
    if g.DATABASE_TYPE == 'sqlite':
        sql_update = sql_update.replace('%s', '?')
        cursor.execute(sql_update, (new_stat, player_db_id))
    else:
        cursor.execute(sql_update, (new_stat, player_db_id))
        
    return float(new_stat)
    
    
#----------------------------------------------------
# --- Konfiguration der Berechnungslogik ---

# --- Konfigurations-Dictionary zur Ermittlung der korrekten Berechnungsfunktion ---
# ANMERKUNG: Diese Funktionen werden im Code weiter unten definiert .
CALCULATION_HANDLERS = {
    'x01'             : _calculate_x01_logic,
    'cricket'         : _calculate_mpr_logic,
    'tactics'         : _calculate_mpr_logic,
    'atc'             : _calculate_hit_rate_logic,
    'countup'         : _calculate_ppr_logic,
    'segment_training': _calculate_hit_rate_logic # Nutzt dieselbe Logik wie ATC
}


#----------------------------------------------------
# === STATISTIK-API FUNKTIONEN ===
def get_all_player_statistics():
    """
    Sammelt umfassende Statistiken für alle Spieler.
    Erweitert für X01: Berechnet zusätzlich gewonnene Matches.
    """
    if not g.USE_DATABASE:
        return []

    stats = {} # Key: Player Name, Value: Dict mit Stats

    with get_db_connection() as conn:
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # --- 1. X01 Statistiken ---
        try:
            # A) Hole Grunddaten aller Spieler
            cursor.execute("SELECT id, name, average FROM players_x01")
            players = cursor.fetchall()
            
            # B) Bereite das Stats-Objekt vor
            player_map = {} # ID -> Name Mapping für spätere Zuordnung
            for p in players:
                # Wenn Tuple-Cursor (Standard)
                p_id = p[0]
                name = p[1]
                avg = p[2]
                player_map[p_id] = name
                
                if name not in stats:
                    stats[name] = {'name': name, 'x01': {}, 'cricket': {}, 'tactics': {}}
                
                stats[name]['x01']['ppr'] = float(avg) if avg else 0.0
                stats[name]['x01']['legs_played'] = 0
                stats[name]['x01']['legs_won'] = 0
                stats[name]['x01']['matches_played'] = 0 # NEU
                stats[name]['x01']['matches_won'] = 0 

            # C) Hole ALLE Leg-Siege für die Match-Auswertung
            # Wir brauchen: match_id, player_id, und ob gewonnen wurde
            if g.DATABASE_TYPE == 'mariadb':
                cursor.execute("SELECT match_id, player_id, is_win FROM games_history_x01")
            else:
                cursor.execute("SELECT match_id, player_id, is_win FROM games_history_x01")
            
            all_legs = cursor.fetchall()

            # D) Daten aggregieren
            # Struktur: matches[match_id][player_id] = anzahl_gewonnene_legs
            matches_analysis = {}

            for row in all_legs:
                m_id = row[0]
                p_id = row[1]
                is_win = row[2] # 1 oder 0

                # Sicherheitscheck, falls ID nicht mehr existiert
                if p_id not in player_map: continue
                name = player_map[p_id]

                # Grundlegende Leg-Statistik zählen
                stats[name]['x01']['legs_played'] += 1
                if is_win:
                    stats[name]['x01']['legs_won'] += 1
                
                # Match-Analyse vorbereiten
                if m_id not in matches_analysis: matches_analysis[m_id] = {}
                if p_id not in matches_analysis[m_id]: matches_analysis[m_id][p_id] = 0
                
                if is_win:
                    matches_analysis[m_id][p_id] += 1

            # E) Match-Gewinner und Match-Anzahl ermitteln
            for m_id, players_scores in matches_analysis.items():
                if not players_scores: continue
                
                # 1. Zähle "Match gespielt" für JEDEN Spieler in diesem Match
                for p_id in players_scores:
                    if p_id in player_map:
                        w_name = player_map[p_id]
                        stats[w_name]['x01']['matches_played'] += 1

                # 2. Ermittle den Gewinner des Matches
                # Finde den Spieler mit den meisten gewonnenen Legs in diesem Match
                winner_id = max(players_scores, key=players_scores.get)
                max_wins = players_scores[winner_id]
                
                # Prüfen auf Eindeutigkeit (kein Unentschieden beim Leg-Count)
                winners = [pid for pid, wins in players_scores.items() if wins == max_wins]
                
                if len(winners) == 1 and max_wins > 0:
                    # Eindeutiger Sieger
                    w_name = player_map[winners[0]]
                    stats[w_name]['x01']['matches_won'] += 1

        except Exception as e:
            logging.error(f"Fehler beim Abrufen der X01-Stats: {e}")


        # --- 2. Cricket Statistiken ---
        try:
            cursor.execute("SELECT id, name, mpr FROM players_cricket")
            players = cursor.fetchall()
            for p in players:
                p_id = p[0]
                name = p[1]
                mpr = p[2]
                
                if name not in stats:
                    stats[name] = {'name': name, 'x01': {}, 'cricket': {}, 'tactics': {}}
                
                stats[name]['cricket']['mpr'] = float(mpr) if mpr else 0.0
                
                # History für Cricket (Anzahl Legs & Wins)
                if g.DATABASE_TYPE == 'mariadb':
                    sql_counts = "SELECT COUNT(*), SUM(is_win) FROM games_history_cricket WHERE player_id = %s"
                    cursor.execute(sql_counts, (p_id,))
                else:
                    sql_counts = "SELECT COUNT(*), SUM(is_win) FROM games_history_cricket WHERE player_id = ?"
                    cursor.execute(sql_counts, (p_id,))
                
                counts = cursor.fetchone()
                stats[name]['cricket']['legs_played'] = counts[0] if counts else 0
                stats[name]['cricket']['legs_won'] = int(counts[1]) if counts and counts[1] else 0

        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Cricket-Stats: {e}")

        # --- 3. Tactics Statistiken ---
        try:
            cursor.execute("SELECT id, name, mpr FROM players_tactics")
            players = cursor.fetchall()
            for p in players:
                p_id = p[0]
                name = p[1]
                mpr = p[2]
                
                if name not in stats:
                    stats[name] = {'name': name, 'x01': {}, 'cricket': {}, 'tactics': {}}
                
                stats[name]['tactics']['mpr'] = float(mpr) if mpr else 0.0
                
                if g.DATABASE_TYPE == 'mariadb':
                    sql_counts = "SELECT COUNT(*), SUM(is_win) FROM games_history_tactics WHERE player_id = %s"
                    cursor.execute(sql_counts, (p_id,))
                else:
                    sql_counts = "SELECT COUNT(*), SUM(is_win) FROM games_history_tactics WHERE player_id = ?"
                    cursor.execute(sql_counts, (p_id,))
                
                counts = cursor.fetchone()
                stats[name]['tactics']['legs_played'] = counts[0] if counts else 0
                stats[name]['tactics']['legs_won'] = int(counts[1]) if counts and counts[1] else 0

        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Tactics-Stats: {e}")

    return list(stats.values())
#----------------------------------------------------
# --- Konfigurations-Dictionary für save_leg_to_history ---
# NEU: Alle Insert-Statements um 'is_win' erweitert.
# Platzhalter: %s (wird für SQLite automatisch zu ?)
SAVE_LEG_CONFIG = {
    'x01': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_average, leg_points, leg_darts, is_win) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        'keys': ['average', 'score', 'dartsThrown']
    },
    'cricket': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_marks, leg_darts, is_win) VALUES (%s, %s, %s, %s, %s, %s)",
        'keys': ['marks', 'darts']
    },
    'tactics': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_marks, leg_darts, is_win) VALUES (%s, %s, %s, %s, %s, %s)",
        'keys': ['marks', 'darts']
    },
    'atc': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_hit_rate, leg_darts, is_win) VALUES (%s, %s, %s, %s, %s, %s)",
        'keys': ['hit_rate', 'darts']
    },
    'countup': {
        'sql': "INSERT INTO {table} (player_id, match_id, leg_number, leg_points, leg_darts, is_win) VALUES (%s, %s, %s, %s, %s, %s)",
        'keys': ['score', 'dartsThrown']
    },
    'segment_training': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_hit_rate, leg_darts, is_win) VALUES (%s, %s, %s, %s, %s, %s)",
        'keys': ['hit_rate', 'darts']
    }
}

#----------------------------------------------------
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