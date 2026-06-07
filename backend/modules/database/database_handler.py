# Backend/modules/core/database_handler.py
#
# Zentrale Datenbankschicht des Backends.
#
# Diese Datei enthält die gesamte Geschäftslogik für Datenbankoperationen.
# Die datenbankspezifischen Eigenheiten (Platzhalter, Cursor-Typen, Verbindungsaufbau)
# werden über austauschbare Adapter-Klassen abstrahiert.
#
# ARCHITEKTUR:
#   database_handler.py          ← Geschäftslogik (diese Datei)
#   database_adapter_base.py     ← Schnittstellen-Definition (Basisklasse)
#   database_adapter_mariadb.py  ← MariaDB-spezifischer Code
#   database_adapter_sqlite.py   ← SQLite-spezifischer Code
#
# Um eine neue Datenbank (z.B. PostgreSQL) hinzuzufügen:
#   1. Neue Datei database_adapter_postgresql.py anlegen
#   2. Die DatabaseAdapter-Basisklasse implementieren
#   3. In init_database_adapter() einen neuen elif-Zweig hinzufügen

import logging
import sys
from contextlib import contextmanager

from ..core import shared_state as g
from ..core import constants as c
from ..core.utils_backend import log_event, log_function_call


# ==============================================================================
# === ADAPTER-INITIALISIERUNG ===
# ==============================================================================

# Der aktive Datenbank-Adapter. Wird einmalig beim Start gesetzt.
_adapter = None

def init_database_adapter():
    """
    Initialisiert den passenden Datenbank-Adapter basierend auf g.DATABASE_TYPE.
    
    Muss nach dem Laden der Konfiguration (load_and_parse_config) aufgerufen werden,
    da g.DATABASE_TYPE zu diesem Zeitpunkt gesetzt sein muss.
    
    Um eine neue Datenbank hinzuzufügen, einfach einen neuen elif-Zweig ergänzen.
    """
    global _adapter

    if not g.USE_DATABASE:
        _adapter = None
        logging.info("Datenbank ist deaktiviert (USE_DATABASE=False). Kein Adapter geladen.")
        return

    db_type = g.DATABASE_TYPE

    if db_type == 'mariadb':
        from .database_adapter_mariadb import MariaDBAdapter
        _adapter = MariaDBAdapter()
        logging.info("Datenbank-Adapter geladen: MariaDB")

    elif db_type == 'sqlite':
        from .database_adapter_sqlite import SQLiteAdapter
        _adapter = SQLiteAdapter()
        logging.info("Datenbank-Adapter geladen: SQLite")

    # --- Erweiterungspunkt für neue Datenbanken ---
    # elif db_type == 'postgresql':
    #     from .database_adapter_postgresql import PostgreSQLAdapter
    #     _adapter = PostgreSQLAdapter()
    #     logging.info("Datenbank-Adapter geladen: PostgreSQL")

    else:
        logging.error("Unbekannter Datenbanktyp: '%s'. Kein Adapter geladen.", db_type)
        _adapter = None


# ==============================================================================
# === 1. ÖFFENTLICHE FUNKTIONEN ===
# ==============================================================================

@contextmanager
@log_function_call
def get_db_connection():
    """
    Stellt eine Datenbankverbindung über einen Context-Manager her.
    Die Entscheidung (MariaDB vs. SQLite vs. ...) wird über den aktiven Adapter getroffen.
    
    Die Verbindung wird bei Eintritt in den 'with'-Block aufgebaut und am Ende
    (auch bei Fehlern) automatisch wieder sicher geschlossen.
    
    Yields:
        Connection: Ein aktives Datenbank-Verbindungsobjekt.
        None: Wenn der Verbindungsaufbau fehlschlägt oder DB deaktiviert ist.
    """
    if not g.USE_DATABASE or _adapter is None:
        yield None
        return
    
    conn = None

    try:
        conn = _adapter.open_connection()
        yield conn
    
    finally:
        # Cleanup: Verbindung schließen, wenn sie noch aktiv ist
        if conn and _adapter.is_connection_alive(conn):
            conn.close()

#----------------------------------------------------

@log_function_call
def get_player_data_from_db(conn, player_name, game_mode):
    """
    Ruft die Stammdaten eines Spielers anhand seines Namens aus der 
    spezifischen 'players'-Tabelle ab.

    Args:
        conn:              Die aktive Datenbank-Verbindung.
        player_name (str): Der Name des zu suchenden Spielers.
        game_mode (str):   Der Spielmodus (z.B. 'x01').

    Returns:
        dict: Ein Dictionary mit den Spalten 'id', 'is_registered' und der Statistik.
        None: Wenn kein Spieler gefunden wurde oder ein Fehler auftrat.
    """
    config = STAT_CONFIG.get(game_mode)
    if not config: return None
        
    table_name = config['player_table']
    column_name = config['column']
    ph = _adapter.placeholder
    
    cursor = _adapter.get_dict_cursor(conn)
    sql = f"SELECT id, is_registered, {column_name} FROM {table_name} WHERE name = {ph}"

    if g.DEBUG:
        logging.info("KONSOLE-AUSGABE (SQL): %s (Parameter: '%s')", sql, player_name)

    try:
        cursor.execute(sql, (player_name,))
        row = cursor.fetchone()
        return _adapter.normalize_row(row, column_name)
        
    except _adapter.get_error_class() as e:
        logging.error("DB-Fehler beim Lesen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

@log_function_call
def create_guest_player(conn, player_name, game_mode):
    """
    Legt einen neuen Spieler als Gast (is_registered = 0) in der 
    spezifischen 'players'-Tabelle an.

    Args:
        conn:              Die aktive Datenbank-Verbindung.
        player_name (str): Der Name des neuen Gast-Spielers.
        game_mode (str):   Der Spielmodus.

    Returns:
        int:  Die automatisch generierte ID des neu erstellten Spielers.
        None: Wenn das Einfügen aufgrund eines Datenbankfehlers fehlschlägt.
    """
    config = STAT_CONFIG.get(game_mode)
    if not config: return None

    table_name = config['player_table']
    ph = _adapter.placeholder
    
    cursor = _adapter.get_cursor(conn)
    sql = f"INSERT INTO {table_name} (name, is_registered) VALUES ({ph}, 0)"

    try:
        if g.DEBUG:
            logging.info("KONSOLE-AUSGABE (SQL): %s (Parameter: '%s')", sql, player_name)
        cursor.execute(sql, (player_name,))
        if g.DEBUG:
            logging.info("==> Neuer Gast-Spieler '%s' mit ID %s wurde in der DB angelegt.", player_name, cursor.lastrowid)
        return cursor.lastrowid
    except _adapter.get_error_class() as e:
        if g.DEBUG:
            logging.error("DB-Fehler beim Anlegen des Spielers '%s': %s", player_name, e)
        return None

#----------------------------------------------------

@log_function_call
def save_leg_to_history(conn, player_db_id, match_id, leg_number, leg_stats, game_mode, is_win=False):
    """
    Speichert die detaillierten Statistiken eines einzelnen, beendeten Legs 
    in der spezifischen 'games_history'-Tabelle.

    Args:
        conn:               Die aktive Datenbank-Verbindung.
        player_db_id (int): Die ID des Spielers aus der 'players'-Tabelle.
        match_id (str):     Die ID des Matches, zu dem das Leg gehört.
        leg_number (int):   Die Nummer des gespielten Legs.
        leg_stats (dict):   Ein Dictionary mit den Statistiken des Legs.
        game_mode (str):    Der Spielmodus.
        is_win (bool):      True, wenn dieser Spieler das Leg gewonnen hat.
    """
    config      = SAVE_LEG_CONFIG.get(game_mode)
    stat_config = STAT_CONFIG.get(game_mode)
    if not config or not stat_config: return
        
    history_table = stat_config['history_table']
    ph = _adapter.placeholder
    
    # SQL aus der Konfig holen und Platzhalter + Tabellennamen einsetzen
    sql = config['sql'].format(table=history_table, ph=ph)
    
    # Boolean in DB-tauglichen Integer wandeln
    win_val = 1 if is_win else 0
    
    # Baut das values-Tupel dynamisch anhand der Konfiguration zusammen
    vals = [player_db_id, match_id, leg_number]
    for key in config['keys']:
        vals.append(leg_stats.get(key, 0))
    # Hänge is_win hinten an
    vals.append(win_val)
    
    values = tuple(vals)

    cursor = _adapter.get_cursor(conn)
    cursor.execute(sql, values)
    conn.commit()

#----------------------------------------------------

@log_function_call
def update_and_register_player(conn, player_db_id, server_stat, game_mode):
    """
    Aktualisiert den Gesamt-Average eines Spielers in der 'players'-Tabelle 
    und setzt gleichzeitig sein 'is_registered'-Flag auf 1.

    Args:
        conn:                   Die aktive Datenbank-Verbindung.
        player_db_id (int):     Die ID des zu aktualisierenden Spielers.
        server_stat (float):    Der vom Autodarts-Server gelieferte Gesamt-Average.
        game_mode (str):        Der Spielmodus.
    """
    config = STAT_CONFIG.get(game_mode)
    if not config: return

    table_name = config['player_table']
    column_name = config['column']
    ph = _adapter.placeholder
    
    cursor = _adapter.get_cursor(conn)
    sql = f"UPDATE {table_name} SET {column_name} = {ph}, is_registered = 1 WHERE id = {ph}"
    cursor.execute(sql, (server_stat, player_db_id))
    conn.commit()

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
    cursor = _adapter.get_dict_cursor(conn)

    handler = CALCULATION_HANDLERS.get(game_mode)
    if handler:
        return handler(cursor, player_db_id, game_mode)
    return 0.0


# ==============================================================================
# === 2. BERECHNUNGSLOGIK ===
# ==============================================================================

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
    ph = _adapter.placeholder
    
    sql_select = f"SELECT SUM(leg_points) as total_points, SUM(leg_darts) as total_darts FROM (SELECT leg_points, leg_darts FROM {history_table} WHERE player_id = {ph} ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    # Der Zugriff auf result['key'] funktioniert aufgrund des Dict-Cursors
    # oder der SQLite Row Factory.
    total_points = result['total_points'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        new_stat = (total_points / total_darts) * 3
        
    sql_update = f"UPDATE {player_table} SET average = {ph} WHERE id = {ph}"
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
    ph = _adapter.placeholder

    sql_select = f"SELECT SUM(leg_marks) as total_marks, SUM(leg_darts) as total_darts FROM (SELECT leg_marks, leg_darts FROM {history_table} WHERE player_id = {ph} ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    total_marks = result['total_marks'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        new_stat = (total_marks * 3) / total_darts
        
    sql_update = f"UPDATE {player_table} SET mpr = {ph} WHERE id = {ph}"
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
    ph = _adapter.placeholder

    sql_select = f"SELECT AVG(leg_hit_rate) as avg_hit_rate FROM (SELECT leg_hit_rate FROM {history_table} WHERE player_id = {ph} ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    new_stat = result['avg_hit_rate'] or 0.0
    
    sql_update = f"UPDATE {player_table} SET hit_rate = {ph} WHERE id = {ph}"
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
    ph = _adapter.placeholder

    sql_select = f"SELECT SUM(leg_points) as total_points, SUM(leg_darts) as total_darts FROM (SELECT leg_points, leg_darts FROM {history_table} WHERE player_id = {ph} ORDER BY finished_at DESC LIMIT 100) AS last_legs;"

    cursor.execute(sql_select, (player_db_id,))
    result = cursor.fetchone()
    
    total_points = result['total_points'] or 0
    total_darts = result['total_darts'] or 0
    new_stat = 0.0
    if total_darts > 0:
        # PPR ist (Punkte / Darts) * 3
        new_stat = (total_points / total_darts) * 3
        
    sql_update = f"UPDATE {player_table} SET ppr = {ph} WHERE id = {ph}"
    cursor.execute(sql_update, (new_stat, player_db_id))
        
    return float(new_stat)

    
# ==============================================================================
# === 3. KONFIGURATIONS-DICTIONARIES ===
# ==============================================================================

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

#----------------------------------------------------
# --- Konfigurations-Dictionary für save_leg_to_history ---
# Die SQL-Statements verwenden {ph} als Platzhalter, der beim Aufruf durch
# den adapterspezifischen Platzhalter (%s oder ?) ersetzt wird.
SAVE_LEG_CONFIG = {
    'x01': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_average, leg_points, leg_darts, is_win) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
        'keys': ['average', 'score', 'dartsThrown']
    },
    'cricket': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_marks, leg_darts, is_win) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
        'keys': ['marks', 'darts']
    },
    'tactics': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_marks, leg_darts, is_win) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
        'keys': ['marks', 'darts']
    },
    'atc': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_hit_rate, leg_darts, is_win) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
        'keys': ['hit_rate', 'darts']
    },
    'countup': {
        'sql': "INSERT INTO {table} (player_id, match_id, leg_number, leg_points, leg_darts, is_win) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
        'keys': ['score', 'dartsThrown']
    },
    'segment_training': {
        'sql':  "INSERT INTO {table} (player_id, match_id, leg_number, leg_hit_rate, leg_darts, is_win) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
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
