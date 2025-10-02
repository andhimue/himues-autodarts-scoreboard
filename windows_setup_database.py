import sys
import json
import argparse
import mariadb

def setup_database(db_config, schema_file):
    """Stellt eine Verbindung her, erstellt die DB und die Tabellen."""
    try:
        print(f"Verbinde mit MariaDB auf {db_config['DB_HOST']}...")
        conn = mariadb.connect(
            host=db_config['DB_HOST'],
            port=int(db_config.get('DB_PORT', 3306)),
            user=db_config['DB_USER'],
            password=db_config['DB_PASSWORD']
        )
        cursor = conn.cursor()
        print("✅ Erfolgreich mit dem MariaDB-Server verbunden.")
        
        db_name = db_config['DB_DATABASE']
        print(f"Erstelle Datenbank '{db_name}' (falls nicht vorhanden)...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE `{db_name}`;")
        print(f"✅ Datenbank '{db_name}' ist bereit.")
        
        print("Erstelle Tabellen...")
        with open(schema_file, "r") as f:
            sql_script = f.read()
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        conn.commit()
        print("✅ Alle Datenbank-Tabellen erfolgreich erstellt.")

    except mariadb.Error as e:
        print(f"❌ Ein Datenbankfehler ist aufgetreten: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Datenbank-Setup-Hilfsskript.')
    parser.add_argument('-dbConfig', required=True, help='JSON-String mit DB-Konfiguration')
    parser.add_argument('-schemaFile', required=True, help='Pfad zur SQL-Schema-Datei')
    
    args = parser.parse_args()
    
    db_config_json = json.loads(args.dbConfig)
    
    setup_database(db_config_json, args.schemaFile)
