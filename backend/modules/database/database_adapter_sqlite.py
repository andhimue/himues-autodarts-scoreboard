# Backend/modules/core/database_adapter_sqlite.py
#
# Adapter für SQLite. Kapselt alle SQLite-spezifischen Eigenheiten:
# - Platzhalter: ?
# - Row Factory: sqlite3.Row (liefert Dict-ähnlichen Zugriff)
# - Row → dict Konvertierung + float-Casting
# - Schema-Initialisierung bei Erstanlage der DB-Datei

import sys
import logging
import sqlite3
from pathlib import Path

from .database_adapter_base import DatabaseAdapter
from ..core import shared_state as g


class SQLiteAdapter(DatabaseAdapter):
    """
    Datenbank-Adapter für SQLite.
    """

    # SQLite verwendet '?' als Platzhalter für parametrisierte Abfragen
    placeholder = '?'

    def open_connection(self):
        """
        Öffnet die SQLite-Verbindung und gibt das Connection-Objekt zurück.
        Erstellt die Datenbankdatei und das Schema, falls sie noch nicht existiert.
        """
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
                self.initialize_schema(conn)

            return conn
            
        except sqlite3.Error as e:
            print(f"FEHLER bei der SQLite-Verbindung: {e}", file=sys.stderr)
            return None

    #----------------------------------------------------

    def get_dict_cursor(self, conn):
        """
        Gibt einen SQLite-Cursor zurück.
        Dank der Row Factory (gesetzt in open_connection) liefert dieser
        bereits Dict-ähnliche sqlite3.Row-Objekte.
        """
        return conn.cursor()

    #----------------------------------------------------

    def get_cursor(self, conn):
        """Gibt einen einfachen SQLite-Cursor zurück (für INSERT/UPDATE)."""
        return conn.cursor()

    #----------------------------------------------------

    def normalize_row(self, row, column_name):
        """
        Normalisiert eine SQLite-Ergebniszeile.
        
        SQLite liefert sqlite3.Row-Objekte, die zwar Dict-ähnlich lesbar sind,
        aber nicht veränderbar. Daher wird hier in ein echtes Dict konvertiert.
        Statistik-Werte werden zu float gecastet, um mit der MariaDB-Ausgabe
        kompatibel zu sein.
        """
        if not row:
            return None
        
        # Das Row-Objekt wird in ein echtes Dict konvertiert
        result_dict = dict(row)
        
        # Konvertierung zu float, um mit der MariaDB-Ausgabe kompatibel zu sein
        if result_dict.get(column_name) is not None:
            result_dict[column_name] = float(result_dict[column_name])
        
        return result_dict

    #----------------------------------------------------

    def is_connection_alive(self, conn):
        """Prüft ob die SQLite-Verbindung noch aktiv ist (einfacher None-Check)."""
        return conn is not None

    #----------------------------------------------------

    def get_error_class(self):
        """Gibt sqlite3.Error als Exception-Klasse zurück."""
        return sqlite3.Error

    #----------------------------------------------------

    def initialize_schema(self, conn):
        """Prüft und erstellt die SQLite-Tabellenstruktur, falls nicht vorhanden."""
        logging.info("SQLite: Überprüfe und erstelle Datenbankstruktur.")
        try:
            # Versuche, das native SQLite-Schema zu laden
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
