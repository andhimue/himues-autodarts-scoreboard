# Backend/modules/core/database_adapter_mariadb.py
#
# Adapter für MariaDB. Kapselt alle MariaDB-spezifischen Eigenheiten:
# - Platzhalter: %s
# - Dict-Cursor: cursor(dictionary=True)
# - Decimal → float Konvertierung
# - Verbindungsprüfung: conn.ping()

import sys
import logging
from decimal import Decimal

from .database_adapter_base import DatabaseAdapter
from ..core import shared_state as g


class MariaDBAdapter(DatabaseAdapter):
    """
    Datenbank-Adapter für MariaDB/MySQL.
    """

    # MariaDB verwendet '%s' als Platzhalter für parametrisierte Abfragen
    placeholder = '%s'

    def open_connection(self):
        """Öffnet die MariaDB-Verbindung und gibt das Connection-Objekt zurück."""
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

    def get_dict_cursor(self, conn):
        """Gibt einen MariaDB-Cursor zurück, der Ergebnisse als Dictionary liefert."""
        return conn.cursor(dictionary=True)

    #----------------------------------------------------

    def get_cursor(self, conn):
        """Gibt einen einfachen MariaDB-Cursor zurück (für INSERT/UPDATE)."""
        return conn.cursor()

    #----------------------------------------------------

    def normalize_row(self, row, column_name):
        """
        Normalisiert eine MariaDB-Ergebniszeile.
        
        MariaDB liefert bei DECIMAL-Spalten Python Decimal-Objekte,
        die für JSON-Serialisierung und Vergleiche zu float konvertiert werden müssen.
        """
        if not row:
            return None
        
        if row.get(column_name) is not None:
            # Prüfe, ob es ein Decimal ist und wandle es in float um
            if isinstance(row[column_name], Decimal):
                row[column_name] = float(row[column_name])
        
        return row

    #----------------------------------------------------

    def is_connection_alive(self, conn):
        """Prüft via ping(), ob die MariaDB-Verbindung noch aktiv ist."""
        try:
            return conn is not None and conn.ping()
        except Exception:
            return False

    #----------------------------------------------------

    def get_error_class(self):
        """Gibt mariadb.Error als Exception-Klasse zurück."""
        import mariadb
        return mariadb.Error

    # MariaDB benötigt kein initialize_schema — die Tabellen werden vom install.py erstellt.
