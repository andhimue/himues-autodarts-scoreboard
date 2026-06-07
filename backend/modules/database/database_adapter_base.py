# Backend/modules/core/database_adapter_base.py
#
# Definiert die Schnittstelle (Basisklasse), die jeder Datenbank-Adapter
# implementieren muss. Neue Datenbanken (z.B. PostgreSQL) können durch
# Erstellen einer neuen Adapter-Klasse hinzugefügt werden, ohne die
# Geschäftslogik in database_handler.py verändern zu müssen.


class DatabaseAdapter:
    """
    Abstrakte Basisklasse für alle Datenbank-Adapter.
    
    Jeder Adapter muss die folgenden Eigenschaften und Methoden implementieren,
    um eine einheitliche Schnittstelle für den database_handler bereitzustellen.
    """

    # Der SQL-Platzhalter für parametrisierte Abfragen.
    # MariaDB verwendet '%s', SQLite verwendet '?'.
    placeholder = None

    def open_connection(self):
        """
        Öffnet eine neue Datenbankverbindung und gibt das Connection-Objekt zurück.
        
        Returns:
            Connection: Ein aktives Datenbank-Verbindungsobjekt.
            None: Wenn der Verbindungsaufbau fehlschlägt.
        """
        raise NotImplementedError

    def get_dict_cursor(self, conn):
        """
        Gibt einen Cursor zurück, der Ergebnisse als Dictionary liefert.
        Wird für SELECT-Abfragen verwendet, bei denen auf Spalten per Name
        zugegriffen werden soll (z.B. row['average']).

        Args:
            conn: Die aktive Datenbank-Verbindung.

        Returns:
            Cursor: Ein Cursor-Objekt mit Dictionary-Zugriff.
        """
        raise NotImplementedError

    def get_cursor(self, conn):
        """
        Gibt einen einfachen Cursor zurück.
        Wird für INSERT/UPDATE-Operationen verwendet.

        Args:
            conn: Die aktive Datenbank-Verbindung.

        Returns:
            Cursor: Ein Standard-Cursor-Objekt.
        """
        raise NotImplementedError

    def normalize_row(self, row, column_name):
        """
        Normalisiert eine einzelne Ergebnis-Zeile zu einem einheitlichen Dictionary
        mit float-Werten für die Statistik-Spalte.
        
        Hintergrund: MariaDB liefert Decimal-Objekte, SQLite liefert sqlite3.Row-Objekte.
        Diese Methode stellt sicher, dass der Aufrufer immer ein normales Dict mit
        float-Werten erhält.

        Args:
            row:          Die rohe Ergebnis-Zeile vom Cursor.
            column_name:  Der Name der Statistik-Spalte (z.B. 'average', 'mpr').

        Returns:
            dict: Ein Dictionary mit normalisierten Werten.
            None: Wenn row None/leer war.
        """
        raise NotImplementedError

    def is_connection_alive(self, conn):
        """
        Prüft, ob eine Datenbankverbindung noch aktiv und nutzbar ist.
        Wird beim Schließen der Verbindung im Context-Manager verwendet.

        Args:
            conn: Die zu prüfende Datenbank-Verbindung.

        Returns:
            bool: True wenn die Verbindung aktiv ist, sonst False.
        """
        raise NotImplementedError

    def get_error_class(self):
        """
        Gibt die datenbankspezifische Exception-Klasse zurück.
        Wird für try/except-Blöcke in der Geschäftslogik verwendet,
        um DB-Fehler sauber abzufangen.

        Returns:
            Exception-Klasse: z.B. mariadb.Error oder sqlite3.Error.
        """
        raise NotImplementedError

    def initialize_schema(self, conn):
        """
        Initialisiert das Datenbankschema (Tabellen erstellen etc.).
        Wird nur aufgerufen, wenn die Datenbank neu erstellt wird.
        
        Nicht alle Adapter müssen dies implementieren — MariaDB z.B. erwartet,
        dass die Tabellen bereits existieren (werden vom install.py erstellt).

        Args:
            conn: Die aktive Datenbank-Verbindung.
        """
        pass  # Standardmäßig nichts tun (z.B. bei MariaDB nicht nötig)
