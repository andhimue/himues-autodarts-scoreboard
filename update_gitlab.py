#!/usr/bin/env python3
# update_gitlab.py - Update-Skript für lokalen GitLab-Server (origin) mit DB-Migration
import os
import sys
import subprocess
import shutil

# --- Konfiguration ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
BACKEND_SERVICE = "himues-scoreboard-backend.service"
FRONTEND_SERVICE = "himues-scoreboard-frontend.service"
TARGET_REMOTE = "origin" # Im GitLab-Kontext ist origin oft der lokale GitLab
TARGET_BRANCH = "main"

# Diese Dateien werden vor dem Reset gesichert und danach wiederhergestellt
FILES_TO_PRESERVE = [
    "backend/config.py",
    "backend/.env",
    "frontend/config_frontend.py"
]

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

def backup_config_files():
    print_info("Sichere lokale Konfigurationsdateien...")
    for rel_path in FILES_TO_PRESERVE:
        full_path = os.path.join(SCRIPT_DIR, rel_path)
        backup_path = full_path + ".update_bak"
        if os.path.exists(full_path):
            shutil.copy2(full_path, backup_path)

def restore_config_files():
    print_info("Stelle lokale Konfigurationsdateien wieder her...")
    for rel_path in FILES_TO_PRESERVE:
        full_path = os.path.join(SCRIPT_DIR, rel_path)
        backup_path = full_path + ".update_bak"
        if os.path.exists(backup_path):
            shutil.move(backup_path, full_path)

def update_database_schema():
    """
    Führt Schema-Updates und Migrationen durch.
    """
    print_header("Datenbank-Schema & Migration")
    python_executable = os.path.join(VENV_DIR, "bin", "python")
    
    # 1. Schema-Update (Spalten hinzufügen) - identischer Inline-Block wie in update.py
    schema_script = """
import os
import sys
import sqlite3
try: import mariadb
except ImportError: mariadb = None
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
    except Exception: pass

cfg = get_config()
conn = None
try:
    if cfg['DATABASE_TYPE'] == 'sqlite':
        conn = sqlite3.connect(os.path.join(BACKEND_DIR, "sqlite", "darts_scoreboard.db"))
    elif cfg['DATABASE_TYPE'] == 'mariadb' and mariadb:
        conn = mariadb.connect(user=cfg['DB_USER'], password=cfg['DB_PASSWORD'], host=cfg['DB_HOST'], port=int(cfg['DB_PORT']), database=cfg['DB_DATABASE'])
    
    if conn:
        cur = conn.cursor()
        tables = ['games_history_x01', 'games_history_cricket', 'games_history_tactics', 'games_history_atc', 'games_history_countup', 'games_history_segment_training']
        col_def = "is_win TINYINT(1) NOT NULL DEFAULT 0" if cfg['DATABASE_TYPE'] == 'mariadb' else "is_win INTEGER NOT NULL DEFAULT 0"
        for t in tables: add_column_if_missing(cur, t, col_def)
        conn.commit()
        conn.close()
except Exception as e: print(f"Schema Update Fehler: {e}")
"""
    print_info("Prüfe und korrigiere Tabellenstruktur (is_win)...")
    try:
        subprocess.run([python_executable, "-c", schema_script], cwd=SCRIPT_DIR, check=True)
    except subprocess.CalledProcessError:
        print_warning("Schema-Update-Check mit Warnung beendet.")

    # 2. Migration
    migrate_script = os.path.join(SCRIPT_DIR, "migrate_database.py")
    if os.path.exists(migrate_script):
        print_info("Führe Daten-Migration aus...")
        run_command([python_executable, migrate_script], cwd=SCRIPT_DIR)

def main():
    print_header("Himues Darts Scoreboard - Update (GitLab)")
    if not os.path.exists(os.path.join(SCRIPT_DIR, ".git")):
        print_error("Kein Git-Repository gefunden!")

    service_mode, systemctl_cmd = get_service_mode()
    print_info(f"Update-Modus: {service_mode.upper()}-Dienste")

    print_header("Stoppe Dienste...")
    run_command(systemctl_cmd + ["stop", BACKEND_SERVICE], ignore_errors=True)
    run_command(systemctl_cmd + ["stop", FRONTEND_SERVICE], ignore_errors=True)
    print_success("Dienste gestoppt.")

    print_header("Aktualisiere Quellcode...")
    backup_config_files()
    print_info(f"Lade neuesten Stand von '{TARGET_REMOTE}'...")
    run_command(["git", "fetch", TARGET_REMOTE], cwd=SCRIPT_DIR)
    print_info(f"Setze lokalen Stand hart auf '{TARGET_REMOTE}/{TARGET_BRANCH}' zurück...")
    run_command(["git", "reset", "--hard", f"{TARGET_REMOTE}/{TARGET_BRANCH}"], cwd=SCRIPT_DIR)
    restore_config_files()
    print_success("Quellcode aktualisiert.")

    print_header("Aktualisiere Python-Abhängigkeiten...")
    pip_executable = os.path.join(VENV_DIR, "bin", "pip")
    if os.path.exists(pip_executable):
        run_command([pip_executable, "install", "-r", "requirements.txt"], cwd=SCRIPT_DIR)
        print_success("Abhängigkeiten aktualisiert.")

    # Datenbank Updates aufrufen
    update_database_schema()

    print_header("Starte Dienste neu...")
    run_command(systemctl_cmd + ["daemon-reload"]) 
    run_command(systemctl_cmd + ["start", BACKEND_SERVICE])
    run_command(systemctl_cmd + ["start", FRONTEND_SERVICE])
    print_success("Dienste gestartet.")
    print_header("Update erfolgreich!")
    print_info(f"Überprüfe die Logs mit: ./show-logs.py")

if __name__ == "__main__":
    main()