#!/usr/bin/env python3
# migrate_database.py

import os
import sys
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Versuche mariadb zu importieren
try:
    import mariadb
except ImportError:
    mariadb = None

# --- Konfiguration ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
CONFIG_FILE = os.path.join(BACKEND_DIR, "config.py")

def _to_bool(value):
    """Hilfsfunktion zur Umwandlung in Boolean."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 't', 'y', 'yes')

def load_config():
    """
    Lädt die Konfiguration strikt nach der Reihenfolge:
    1. Standardwerte
    2. backend/config.py
    3. backend/.env
    """
    # 1. Standardwerte
    cfg = {
        'USE_DATABASE': False,
        'DATABASE_TYPE': 'none',
        'DB_HOST': '127.0.0.1',
        'DB_PORT': 3306,
        'DB_USER': '',
        'DB_PASSWORD': '',
        'DB_DATABASE': ''
    }

    # 2. backend/config.py
    if os.path.exists(CONFIG_FILE):
        try:
            config_vars = {}
            with open(CONFIG_FILE, 'r') as f:
                exec(f.read(), {}, config_vars)
            for key in cfg.keys():
                if key in config_vars:
                    cfg[key] = config_vars[key]
        except Exception as e:
            print(f"⚠️  Warnung: Fehler beim Lesen der {CONFIG_FILE}: {e}")

    # 3. .env
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        for key in cfg.keys():
            env_val = os.getenv(key)
            if env_val is not None:
                cfg[key] = env_val

    # 4. Normalisierung
    cfg['USE_DATABASE'] = _to_bool(cfg['USE_DATABASE'])
    cfg['DATABASE_TYPE'] = str(cfg['DATABASE_TYPE']).lower()
    try:
        cfg['DB_PORT'] = int(cfg['DB_PORT'])
    except (ValueError, TypeError):
        cfg['DB_PORT'] = 3306

    return cfg

def migrate_x01_wins(conn, db_type):
    print("  -> Analysiere X01 Legs (Basis: Punkte)...")
    cursor = conn.cursor()
    
    if db_type == 'sqlite':
        sql = """
            UPDATE games_history_x01
            SET is_win = 1
            WHERE id IN (
                SELECT t1.id
                FROM games_history_x01 t1
                JOIN (
                    SELECT match_id, leg_number, MAX(leg_points) as max_val
                    FROM games_history_x01
                    GROUP BY match_id, leg_number
                ) t2 ON t1.match_id = t2.match_id 
                    AND t1.leg_number = t2.leg_number 
                    AND t1.leg_points = t2.max_val
            );
        """
    else:
        sql = """
            UPDATE games_history_x01 t1
            JOIN (
                SELECT match_id, leg_number, MAX(leg_points) as max_val
                FROM games_history_x01
                GROUP BY match_id, leg_number
            ) t2 ON t1.match_id = t2.match_id 
                AND t1.leg_number = t2.leg_number 
                AND t1.leg_points = t2.max_val
            SET t1.is_win = 1;
        """
    
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"  ✅ X01 Migration erfolgreich. {cursor.rowcount} Datensätze aktualisiert.")
    except Exception as e:
        print(f"  ❌ Fehler bei X01 Migration: {e}")

def migrate_cricket_tactics_wins(conn, db_type, table_name, mode_name):
    """
    Migriert Cricket oder Tactics.
    Logik: Wir nutzen 'leg_marks' als Indikator. Der Spieler mit den meisten Marks
    wird als Gewinner angenommen. Das ist die beste Annäherung für historische Daten.
    """
    print(f"  -> Analysiere {mode_name} Legs (Basis: Marks)...")
    cursor = conn.cursor()
    
    if db_type == 'sqlite':
        sql = f"""
            UPDATE {table_name}
            SET is_win = 1
            WHERE id IN (
                SELECT t1.id
                FROM {table_name} t1
                JOIN (
                    SELECT match_id, leg_number, MAX(leg_marks) as max_val
                    FROM {table_name}
                    GROUP BY match_id, leg_number
                ) t2 ON t1.match_id = t2.match_id 
                    AND t1.leg_number = t2.leg_number 
                    AND t1.leg_marks = t2.max_val
            );
        """
    else:
        sql = f"""
            UPDATE {table_name} t1
            JOIN (
                SELECT match_id, leg_number, MAX(leg_marks) as max_val
                FROM {table_name}
                GROUP BY match_id, leg_number
            ) t2 ON t1.match_id = t2.match_id 
                AND t1.leg_number = t2.leg_number 
                AND t1.leg_marks = t2.max_val
            SET t1.is_win = 1;
        """
    
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"  ✅ {mode_name} Migration erfolgreich. {cursor.rowcount} Datensätze aktualisiert.")
    except Exception as e:
        print(f"  ❌ Fehler bei {mode_name} Migration: {e}")

def main():
    print("--- Starte Datenbank-Migration ---")
    cfg = load_config()
    
    if not cfg['USE_DATABASE'] or cfg['DATABASE_TYPE'] == 'none':
        print("Datenbank ist deaktiviert. Abbruch.")
        return

    conn = None
    try:
        if cfg['DATABASE_TYPE'] == 'sqlite':
            db_path = os.path.join(BACKEND_DIR, "sqlite", "darts_scoreboard.db")
            print(f"Verbinde mit SQLite: {db_path}")
            conn = sqlite3.connect(db_path)
        
        elif cfg['DATABASE_TYPE'] == 'mariadb':
            print(f"Verbinde mit MariaDB: {cfg['DB_HOST']}")
            if not mariadb:
                print("❌ Fehler: 'mariadb' Modul fehlt.")
                sys.exit(1)
            conn = mariadb.connect(
                user=cfg['DB_USER'],
                password=cfg['DB_PASSWORD'],
                host=cfg['DB_HOST'],
                port=cfg['DB_PORT'],
                database=cfg['DB_DATABASE']
            )
        else:
            print(f"Unbekannter Typ: {cfg['DATABASE_TYPE']}")
            return

        # --- Migrationen ausführen ---
        migrate_x01_wins(conn, cfg['DATABASE_TYPE'])
        migrate_cricket_tactics_wins(conn, cfg['DATABASE_TYPE'], 'games_history_cricket', 'Cricket')
        migrate_cricket_tactics_wins(conn, cfg['DATABASE_TYPE'], 'games_history_tactics', 'Tactics')
        
    except Exception as e:
        print(f"❌ Kritischer Fehler: {e}")
    finally:
        if conn:
            conn.close()
            print("Verbindung geschlossen.")

if __name__ == "__main__":
    main()