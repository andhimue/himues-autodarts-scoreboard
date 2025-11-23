#!/usr/bin/env python3
# update.py - Standard Update-Skript für GitHub (origin)
import os
import sys
import subprocess
import shutil

# --- Konfiguration ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
BACKEND_SERVICE = "himues-scoreboard-backend.service"
FRONTEND_SERVICE = "himues-scoreboard-frontend.service"
TARGET_REMOTE = "origin"
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
    """Sichert Konfigurationsdateien in temporäre .bak Dateien."""
    print_info("Sichere lokale Konfigurationsdateien...")
    for rel_path in FILES_TO_PRESERVE:
        full_path = os.path.join(SCRIPT_DIR, rel_path)
        backup_path = full_path + ".update_bak"
        if os.path.exists(full_path):
            shutil.copy2(full_path, backup_path)

def restore_config_files():
    """Stellt Konfigurationsdateien aus .bak Dateien wieder her."""
    print_info("Stelle lokale Konfigurationsdateien wieder her...")
    for rel_path in FILES_TO_PRESERVE:
        full_path = os.path.join(SCRIPT_DIR, rel_path)
        backup_path = full_path + ".update_bak"
        if os.path.exists(backup_path):
            shutil.move(backup_path, full_path)

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

    # 2. Git Update
    print_header("Aktualisiere Quellcode...")
    
    # SCHRITT A: Manuelles Backup der Configs
    backup_config_files()

    print_info(f"Lade neuesten Stand von '{TARGET_REMOTE}'...")
    run_command(["git", "fetch", TARGET_REMOTE], cwd=SCRIPT_DIR)
    
    print_info(f"Setze lokalen Stand hart auf '{TARGET_REMOTE}/{TARGET_BRANCH}' zurück...")
    run_command(["git", "reset", "--hard", f"{TARGET_REMOTE}/{TARGET_BRANCH}"], cwd=SCRIPT_DIR)
    
    # SCHRITT B: Restore der Configs (überschreibt die Server-Version)
    restore_config_files()
    
    print_success("Quellcode aktualisiert.")

    # 3. Abhängigkeiten
    print_header("Aktualisiere Python-Abhängigkeiten...")
    pip_executable = os.path.join(VENV_DIR, "bin", "pip")
    if os.path.exists(pip_executable):
        run_command([pip_executable, "install", "-r", "requirements.txt"], cwd=SCRIPT_DIR)
        print_success("Abhängigkeiten aktualisiert.")
    else:
        print_warning(f"Virtuelle Umgebung nicht gefunden unter: {VENV_DIR}")

    # 4. Dienste starten
    print_header("Starte Dienste neu...")
    run_command(systemctl_cmd + ["daemon-reload"]) 
    run_command(systemctl_cmd + ["start", BACKEND_SERVICE])
    run_command(systemctl_cmd + ["start", FRONTEND_SERVICE])
    print_success("Dienste gestartet.")

    print_header("Update erfolgreich!")
    print_info(f"Überprüfe die Logs mit: ./show-logs.py")

if __name__ == "__main__":
    main()