#!/usr/bin/env python3
# update.py - Standard Update-Skript für GitHub (origin) mit Smart-Config-Merge & DB-Migration
import os
import sys
import subprocess
import shutil
import re

# --- Konfiguration ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
BACKEND_SERVICE = "himues-scoreboard-backend.service"
FRONTEND_SERVICE = "himues-scoreboard-frontend.service"
TARGET_REMOTE = "origin"
TARGET_BRANCH = "main"

# Config-Dateien, die gemerged werden sollen
CONFIG_BACKEND = "backend/config.py"
CONFIG_FRONTEND = "frontend/config_frontend.py"
FILES_TO_PROCESS = [CONFIG_BACKEND, CONFIG_FRONTEND]
ENV_FILE = "backend/.env"

# --- Farbdefinitionen ---
class color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(message): print(f"\n{color.HEADER}{color.BOLD}--- {message} ---{color.END}")
def print_success(message): print(f"{color.GREEN}✅ {message}{color.END}")
def print_info(message): print(f"{color.BLUE}ℹ️  {message}{color.END}")
def print_warning(message): print(f"{color.YELLOW}⚠️  {message}{color.END}")
def print_error(message): print(f"{color.RED}❌ {message}{color.END}"); sys.exit(1)

def run_command(command, cwd=None, shell=False, ignore_errors=False):
    try:
        subprocess.check_call(command, cwd=cwd, shell=shell)
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            print_error(f"Fehler bei Befehl: {' '.join(command) if isinstance(command, list) else command}")
        else:
            print_warning(f"Warnung bei Befehl: {' '.join(command) if isinstance(command, list) else command}")

def get_service_mode():
    if os.geteuid() == 0:
        return "system", ["systemctl"]
    else:
        return "user", ["systemctl", "--user"]

# --- Config Merge Logik ---

def parse_config_values(file_path):
    """Liest eine Python-Config-Datei und extrahiert Variablen und ihre Werte."""
    values = {}
    if not os.path.exists(file_path):
        return values
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    try:
        local_scope = {}
        exec(content, {}, local_scope)
        # Filtere Module und interne Variablen (__...) raus
        for key, val in local_scope.items():
            if not key.startswith('_') and not hasattr(val, '__name__'): 
                values[key] = val
    except Exception as e:
        print_warning(f"Konnte Werte aus {file_path} nicht via exec() parsen: {e}. Nutze Regex-Fallback.")
        # Fallback: Einfaches Regex Parsing
        with open(file_path, 'r') as f:
            for line in f:
                match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)', line.strip())
                if match:
                    values[match.group(1)] = match.group(2)
                    
    return values

def format_python_value(value):
    """Formatiert einen Python-Wert zurück in einen String für die Config-Datei."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return str(value) # True/False
    return repr(value) # Fallback für Listen, Dicts, Zahlen

def merge_configs(target_file, source_values):
    """
    Liest die NEUE Config-Datei (vom Repo) Zeile für Zeile und ersetzt
    Werte, wenn sie in den alten User-Werten (source_values) vorhanden sind.
    Behält Kommentare und Struktur der NEUEN Datei bei.
    """
    if not os.path.exists(target_file):
        return

    print_info(f"Merge Konfiguration für {target_file}...")
    
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip_mode = False # Um alte Multiline-Blöcke zu überspringen

    for line in lines:
        # Skip-Logik für mehrzeilige Werte im Template (falls vorhanden)
        if skip_mode:
            if line.strip().startswith('}') or line.strip().startswith(']'):
                skip_mode = False
            continue

        match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=', line.strip())
        if match:
            var_name = match.group(1)
            
            # Prüfen, ob wir für diese Variable einen alten Wert haben
            if var_name in source_values:
                old_val = source_values[var_name]
                
                # Inline-Kommentare retten
                inline_comment = ''
                if '#' in line:
                    parts = line.split('#', 1)
                    # Prüfen ob das # nicht Teil eines Strings ist
                    if not (parts[0].count('"') % 2 == 1 or parts[0].count("'") % 2 == 1):
                        inline_comment = ' # ' + parts[1].strip()

                # Einrückung beibehalten
                indentation = re.match(r'^\s*', line).group(0)
                
                formatted_val = format_python_value(old_val)
                new_lines.append(f"{indentation}{var_name} = {formatted_val}{inline_comment}\n")
                
                # Wenn die Originalzeile einen Block startete, müssen wir den Rest des Blocks im Template überspringen
                val_part = line.split('=', 1)[1].strip()
                if val_part.startswith('{') and not '}' in val_part:
                    skip_mode = True
                if val_part.startswith('[') and not ']' in val_part:
                    skip_mode = True
            else:
                # Variable ist neu im Repo -> Zeile unverändert übernehmen
                new_lines.append(line)
        else:
            # Keine Zuweisung -> Kommentar oder Leerzeile -> übernehmen
            new_lines.append(line)

    with open(target_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def backup_user_configs():
    """Liest die aktuellen Werte aus den Configs und speichert sie im Speicher."""
    configs = {}
    print_info("Lese aktuelle Benutzer-Konfigurationen...")
    
    # 1. .env sichern (wird einfach kopiert, da keine Struktur)
    env_path = os.path.join(SCRIPT_DIR, ENV_FILE)
    if os.path.exists(env_path):
        shutil.copy2(env_path, env_path + ".bak")
    
    # 2. Python Configs parsen
    for rel_path in FILES_TO_PROCESS:
        full_path = os.path.join(SCRIPT_DIR, rel_path)
        if os.path.exists(full_path):
            # Sicherheits-Backup der ganzen Datei
            shutil.copy2(full_path, full_path + ".bak_full")
            # Werte parsen
            configs[rel_path] = parse_config_values(full_path)
            
    return configs

def restore_and_merge_configs(saved_values):
    """Stellt .env wieder her und mergt Python-Configs."""
    print_info("Stelle Konfigurationen wieder her (Merge)...")
    
    # 1. .env wiederherstellen
    env_path = os.path.join(SCRIPT_DIR, ENV_FILE)
    if os.path.exists(env_path + ".bak"):
        shutil.move(env_path + ".bak", env_path)
        
    # 2. Python Configs mergen
    for rel_path, values in saved_values.items():
        full_path = os.path.join(SCRIPT_DIR, rel_path)
        if os.path.exists(full_path):
            merge_configs(full_path, values)
        else:
            print_warning(f"Neue Config {rel_path} nicht gefunden. Kann nicht mergen.")

# --- Datenbank Update Logik ---

def update_database_schema():
    """
    Führt Schema-Updates (Spalten hinzufügen) und Daten-Migrationen durch.
    """
    print_header("Datenbank-Schema & Migration")
    
    python_executable = os.path.join(VENV_DIR, "bin", "python")
    
    # 1. Schema-Update (Spalten 'is_win' hinzufügen falls fehlend)
    schema_script = """
import os
import sys
import sqlite3
try:
    import mariadb
except ImportError:
    mariadb = None
from dotenv import load_dotenv

SCRIPT_DIR = os.getcwd()
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
CONFIG_FILE = os.path.join(BACKEND_DIR, "config.py")

def get_config():
    c = {'DATABASE_TYPE': 'sqlite', 'DB_HOST': '127.0.0.1', 'DB_PORT': 3306, 'DB_USER': 'root', 'DB_PASSWORD': '', 'DB_DATABASE': 'himues_darts_db'}
    if os.path.exists(CONFIG_FILE):
        try:
            cf = {}
            with open(CONFIG_FILE, 'r') as f: exec(f.read(), {}, cf)
            for k in c.keys(): 
                if k in cf: c[k] = cf[k]
        except: pass
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        for k in c.keys():
            v = os.getenv(k)
            if v is not None: c[k] = v
    c['DATABASE_TYPE'] = str(c.get('DATABASE_TYPE', 'sqlite')).lower()
    return c

def add_column_if_missing(cursor, table, col_def):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        print(f"  -> Spalte 'is_win' hinzugefügt zu {table}")
    except Exception:
        pass

cfg = get_config()
conn = None

try:
    if cfg['DATABASE_TYPE'] == 'sqlite':
        db = os.path.join(BACKEND_DIR, "sqlite", "darts_scoreboard.db")
        conn = sqlite3.connect(db)
    elif cfg['DATABASE_TYPE'] == 'mariadb' and mariadb:
        conn = mariadb.connect(user=cfg['DB_USER'], password=cfg['DB_PASSWORD'], host=cfg['DB_HOST'], port=int(cfg['DB_PORT']), database=cfg['DB_DATABASE'])
    
    if conn:
        cur = conn.cursor()
        tables = ['games_history_x01', 'games_history_cricket', 'games_history_tactics', 'games_history_atc', 'games_history_countup', 'games_history_segment_training']
        col_def = "is_win TINYINT(1) NOT NULL DEFAULT 0" if cfg['DATABASE_TYPE'] == 'mariadb' else "is_win INTEGER NOT NULL DEFAULT 0"
        
        for t in tables:
            add_column_if_missing(cur, t, col_def)
        conn.commit()
        conn.close()
except Exception as e:
    print(f"Schema Update Fehler: {e}")
"""
    
    print_info("Prüfe und korrigiere Tabellenstruktur (is_win)...")
    try:
        subprocess.run([python_executable, "-c", schema_script], cwd=SCRIPT_DIR, check=True)
    except subprocess.CalledProcessError:
        print_warning("Schema-Update-Check mit Warnung beendet (evtl. DB nicht erreichbar).")

    # 2. Daten-Migration (Gewinner nachträglich berechnen)
    migrate_script = os.path.join(SCRIPT_DIR, "migrate_database.py")
    if os.path.exists(migrate_script):
        print_info("Führe Daten-Migration aus (migrate_database.py)...")
        run_command([python_executable, migrate_script], cwd=SCRIPT_DIR)
    else:
        print_warning("migrate_database.py nicht gefunden. Überspringe Daten-Migration.")


# --- HAUPTPROGRAMM ---

def main():
    print_header("Himues Darts Scoreboard - Update (GitHub)")
    
    if not os.path.exists(os.path.join(SCRIPT_DIR, ".git")):
        print_error("Kein Git-Repository gefunden!")

    service_mode, systemctl_cmd = get_service_mode()
    print_info(f"Update-Modus: {service_mode.upper()}-Dienste")

    # 1. Dienste stoppen
    print_header("Stoppe Dienste...")
    run_command(systemctl_cmd + ["stop", BACKEND_SERVICE], ignore_errors=True)
    run_command(systemctl_cmd + ["stop", FRONTEND_SERVICE], ignore_errors=True)
    print_success("Dienste gestoppt.")

    # 2. Git Update mit Smart Merge
    print_header("Aktualisiere Quellcode...")
    
    # A. Werte sichern
    saved_config_values = backup_user_configs()

    print_info(f"Lade neuesten Stand von '{TARGET_REMOTE}'...")
    run_command(["git", "fetch", TARGET_REMOTE], cwd=SCRIPT_DIR)
    
    print_info(f"Setze lokalen Stand hart auf '{TARGET_REMOTE}/{TARGET_BRANCH}' zurück...")
    run_command(["git", "reset", "--hard", f"{TARGET_REMOTE}/{TARGET_BRANCH}"], cwd=SCRIPT_DIR)
    
    # B. Werte in neue Dateien mergen
    restore_and_merge_configs(saved_config_values)
    
    print_success("Quellcode aktualisiert und Konfigurationen gemerged.")

    # 3. Abhängigkeiten
    print_header("Aktualisiere Python-Abhängigkeiten...")
    pip_executable = os.path.join(VENV_DIR, "bin", "pip")
    if os.path.exists(pip_executable):
        run_command([pip_executable, "install", "-r", "requirements.txt"], cwd=SCRIPT_DIR)
        print_success("Abhängigkeiten aktualisiert.")
    else:
        print_warning(f"Virtuelle Umgebung nicht gefunden unter: {VENV_DIR}")

    # 4. Datenbank Updates
    update_database_schema()

    # 5. Dienste starten
    print_header("Starte Dienste neu...")
    run_command(systemctl_cmd + ["daemon-reload"]) 
    run_command(systemctl_cmd + ["start", BACKEND_SERVICE])
    run_command(systemctl_cmd + ["start", FRONTEND_SERVICE])
    print_success("Dienste gestartet.")

    print_header("Update erfolgreich!")
    print_info(f"Überprüfe die Logs mit: ./show-logs.py")

if __name__ == "__main__":
    main()