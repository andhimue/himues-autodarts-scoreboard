#!/usr/bin/env python3

#
# Dieses Script updated himues-scoreboard von github
# und behält dabei die Konfiguration bei
#


import os
import sys
import subprocess
import time

# --- Konfiguration ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
BACKEND_SERVICE = "himues-scoreboard-backend.service"
FRONTEND_SERVICE = "himues-scoreboard-frontend.service"

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
def print_info(message): print(f"{color.BLUE}ℹ️  {message}{Color.END}")
def print_warning(message): print(f"{color.YELLOW}⚠️  {message}{color.END}")
def print_error(message): print(f"{color.RED}❌ {message}{color.END}"); sys.exit(1)

def run_command(command, cwd=None, shell=False, ignore_errors=False):
    """Führt einen Befehl aus und gibt bei Fehler ab (außer ignore_errors=True)."""
    try:
        subprocess.check_call(command, cwd=cwd, shell=shell)
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            print_error(f"Fehler bei Befehl: {' '.join(command) if isinstance(command, list) else command}")
        else:
            print_warning(f"Warnung bei Befehl: {' '.join(command) if isinstance(command, list) else command}")

def get_service_mode():
    """Prüft, ob wir Root sind (System-Dienste) oder User (User-Dienste)."""
    if os.geteuid() == 0:
        return "system", ["systemctl"]
    else:
        return "user", ["systemctl", "--user"]

def main():
    print_header("Himues Darts Scoreboard - Update Assistent")
    
    # 1. Prüfen, ob wir in einem Git-Repo sind
    if not os.path.exists(os.path.join(SCRIPT_DIR, ".git")):
        print_error("Kein Git-Repository gefunden! Updates funktionieren nur, wenn das Projekt via 'git clone' installiert wurde.")

    service_mode, systemctl_cmd = get_service_mode()
    print_info(f"Update-Modus: {service_mode.upper()}-Dienste")

    # 2. Dienste stoppen
    print_header("Stoppe Dienste...")
    run_command(systemctl_cmd + ["stop", BACKEND_SERVICE], ignore_errors=True)
    run_command(systemctl_cmd + ["stop", FRONTEND_SERVICE], ignore_errors=True)
    print_success("Dienste gestoppt.")

    # 3. Git Pull (Code aktualisieren)
    print_header("Aktualisiere Quellcode via Git...")
    # Stash: Speichert lokale Änderungen temporär, um Konflikte zu vermeiden
    print_info("Sichere lokale Änderungen (Stash)...")
    run_command(["git", "stash"], cwd=SCRIPT_DIR)
    
    print_info("Lade Updates herunter (Pull)...")
    run_command(["git", "pull"], cwd=SCRIPT_DIR)
    
    # Versuchen, lokale Änderungen wieder anzuwenden. Kann zu Konflikten führen, 
    # wenn config.py geändert wurde, aber meistens klappt es oder ist für .env egal.
    print_info("Stelle lokale Änderungen wieder her (Stash Pop)...")
    run_command(["git", "stash", "pop"], cwd=SCRIPT_DIR, ignore_errors=True)
    print_success("Quellcode aktualisiert.")

    # 4. Abhängigkeiten aktualisieren
    print_header("Aktualisiere Python-Abhängigkeiten...")
    pip_executable = os.path.join(VENV_DIR, "bin", "pip")
    if not os.path.exists(pip_executable):
        print_error(f"Virtuelle Umgebung nicht gefunden unter: {VENV_DIR}")
    
    run_command([pip_executable, "install", "-r", "requirements.txt"], cwd=SCRIPT_DIR)
    print_success("Abhängigkeiten aktualisiert.")

    # 5. Dienste neu starten
    print_header("Starte Dienste neu...")
    run_command(systemctl_cmd + ["daemon-reload"]) # Sicherheitshalber, falls Service-Files geändert wurden
    run_command(systemctl_cmd + ["start", BACKEND_SERVICE])
    run_command(systemctl_cmd + ["start", FRONTEND_SERVICE])
    print_success("Dienste gestartet.")

    print_header("Update erfolgreich abgeschlossen!")
    print_info(f"Überprüfe die Logs mit: ./show-logs.py")

if __name__ == "__main__":
    main()
