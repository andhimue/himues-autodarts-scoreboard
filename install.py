#!/usr/bin/env python3
import os
import sys
import subprocess
import getpass
import re
import shutil
import socket
import json
from datetime import datetime, timedelta


# --- Konfiguration ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
REQUIREMENTS_FILE = os.path.join(SCRIPT_DIR, "requirements.txt")
CONFIG_FILE = os.path.join(BACKEND_DIR, "config.py")
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
DB_SCHEMA_FILE = os.path.join(BACKEND_DIR, "docs", "database_schema.sql")

# --- Farbdefinitionen ---
class color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

#-------------------------------------------------------------------------
    
def print_header(message):
    print(f"\n{color.HEADER}{color.BOLD}--- {message} ---{color.END}")

#-------------------------------------------------------------------------
    
def print_success(message):
    print(f"{color.GREEN}✅ {message}{color.END}")

#-------------------------------------------------------------------------

def print_info(message):
    print(f"{color.BLUE}ℹ️  {message}{color.END}")

#-------------------------------------------------------------------------
    
def print_warning(message):
    print(f"{color.YELLOW}⚠️  {message}{color.END}")

#-------------------------------------------------------------------------
    
def print_error(message, exit_script=True):
    print(f"{color.RED}❌ {message}{color.END}")
    if exit_script:
        sys.exit(1)

#-------------------------------------------------------------------------
    
def ask_question(prompt, default="y"):
    options = "[Y/n]" if default.lower() == "y" else "[y/N]"
    answer = input(f"{color.YELLOW}❓ {prompt} {options}: {color.END}").lower().strip()
    if not answer:
        return default.lower() == "y"
    return answer.startswith('y')

#-------------------------------------------------------------------------

def check_and_install_venv(USE_SUDO):
    """Prüft, ob das venv-Modul verfügbar ist, und installiert es bei Bedarf."""
    try:
        import ensurepip
        return
    except ImportError:
        print_warning("Das Python-Modul 'venv' scheint nicht installiert zu sein.")
        try:
            subprocess.check_call(["which", "apt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print_error("apt-Paketmanager nicht gefunden. Bitte installiere das 'python3-venv' Paket manuell.")
        if not ask_question("Soll versucht werden, das Paket 'python3-venv' automatisch zu installieren?"):
            print_error("Installation abgebrochen. Bitte installiere 'python3-venv' manuell.")
        try:
            py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            package_name = f"python{py_version}-venv"
            print(f"Versuche, das Paket '{package_name}' zu installieren...")
            print_warning("Für die Installation wird dein administratives Passwort (sudo) benötigt.")
            subprocess.check_call(USE_SUDO + ["apt", "update"])
            subprocess.check_call(USE_SUDO + ["apt", "install", "-y", package_name])
            print_success(f"'{package_name}' wurde erfolgreich installiert.")
            print_header("Skript wird neu gestartet...")
            os.execv(sys.executable, ['python3'] + sys.argv)
        except Exception as e:
            print_error(f"Installation von '{package_name}' fehlgeschlagen: {e}")

#-------------------------------------------------------------------------
    
def check_and_install_mariadb_dev(USE_SUDO):
    """Prüft, ob MariaDB Connector/C (libmariadb-dev) installiert ist."""
    if shutil.which("mariadb_config"):
        return True
    print_warning("Die MariaDB-Entwicklungsdateien (Connector/C) scheinen zu fehlen.")
    try:
        subprocess.check_call(["which", "apt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print_error("apt-Paketmanager nicht gefunden. Bitte installiere 'libmariadb-dev' manuell.", exit_script=False)
        return False
    if not ask_question("Soll versucht werden, das Paket 'libmariadb-dev' automatisch zu installieren?"):
        return False
    try:
        package_name = "libmariadb-dev"
        print(f"Versuche, das Paket '{package_name}' zu installieren...")
        print_warning("Für die Installation wird dein administratives Passwort (sudo) benötigt.")
        subprocess.check_call(USE_SUDO + ["apt", "install", "-y", package_name])
        print_success(f"'{package_name}' wurde erfolgreich installiert.")
        return True
    except Exception as e:
        print_error(f"Installation von '{package_name}' fehlgeschlagen: {e}", exit_script=False)
        return False

#-------------------------------------------------------------------------
    
def check_and_install_build_tools(USE_SUDO):
    """Prüft, ob der C-Compiler und Python-Entwicklungs-Header installiert sind."""
    try:
        from distutils.sysconfig import get_python_inc
        headers_available = os.path.exists(os.path.join(get_python_inc(), 'Python.h'))
    except Exception:
        headers_available = False

    if shutil.which("gcc") and headers_available:
        return
    
    print_warning("Die Build-Werkzeuge (C-Compiler/Python-dev) scheinen zu fehlen.")
    try:
        subprocess.check_call(["which", "apt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print_error("apt-Paketmanager nicht gefunden. Bitte installiere 'build-essential' und 'python3-dev' manuell.")
    if not ask_question("Sollen die Pakete 'build-essential' und 'python3-dev' automatisch installiert werden?"):
        print_error("Installation abgebrochen. Bitte installiere die Pakete manuell.")
    try:
        packages = ["build-essential", "python3-dev"]
        print(f"Versuche, die Pakete '{' und '.join(packages)}' zu installieren...")
        print_warning("Für die Installation wird dein administratives Passwort (sudo) benötigt.")
        subprocess.check_call(USE_SUDO + ["apt", "install", "-y"] + packages)
        print_success(f"Die Build-Werkzeuge wurden erfolgreich installiert.")
    except Exception as e:
        print_error(f"Installation der Build-Werkzeuge fehlgeschlagen: {e}")

#-------------------------------------------------------------------------
    
def check_system():
    print_header("System-Prüfung")
    if not sys.version_info >= (3, 8):
        print_error("Python 3.8 oder höher wird benötigt. Installation abgebrochen.")
    print_success("Python-Version ist ausreichend.")

#-------------------------------------------------------------------------
    
def setup_venv():
    """Richtet die venv ein und installiert die Core-Abhängigkeiten."""
    print_header("Virtuelle Umgebung (venv) und Core-Abhängigkeiten")
    
    if not os.path.exists(VENV_DIR):
        print("Erstelle virtuelle Umgebung...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
        print_success("Virtuelle Umgebung erfolgreich erstellt.")
    else:
        print_success("Virtuelle Umgebung existiert bereits.")

    pip_executable = os.path.join(VENV_DIR, "bin", "pip")

    print("Installiere Core-Abhängigkeiten aus requirements.txt...")
    try:
        subprocess.check_call([pip_executable, "install", "-r", REQUIREMENTS_FILE])
        print_success("Core-Abhängigkeiten erfolgreich installiert.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_error(f"Fehler bei der Installation der Core-Abhängigkeiten: {e}")

def install_mariadb_dependencies(USE_SUDO):
    """Installiert die System- und Python-Abhängigkeiten für MariaDB."""
    print_info("MariaDB-Option gewählt. Prüfe und installiere MariaDB-Abhängigkeiten...")
    
    if not check_and_install_mariadb_dev(USE_SUDO):
        print_warning("MariaDB System-Bibliothek (libmariadb-dev) konnte nicht installiert werden.")
        return False

    pip_executable = os.path.join(VENV_DIR, "bin", "pip")
    try:
        print("Installiere das 'mariadb' Python-Paket in die venv...")
        subprocess.check_call([pip_executable, "install", "mariadb"])
        print_success("'mariadb'-Paket erfolgreich installiert.")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Fehler bei der Installation des 'mariadb'-Pakets: {e}", exit_script=False)
        return False

#-------------------------------------------------------------------------
    
def get_db_credentials():
    print("Bitte gib die Zugangsdaten für deine MariaDB-Instanz ein.")
    db_config = {}
    db_config['DB_HOST'] = input("    Datenbank-Host [localhost]: ") or "localhost"
    db_config['DB_PORT'] = input("    Datenbank-Port [3306]: ") or "3306"
    db_config['DB_USER'] = input("    Datenbank-Benutzer (z.B. himues_darts): ") or "himues_darts"
    db_config['DB_PASSWORD'] = getpass.getpass("    Datenbank-Passwort: ")
    db_config['DB_DATABASE'] = input("    Name für die neue Darts-Datenbank [himues_darts_db]: ") or "himues_darts_db"
    return db_config

#-------------------------------------------------------------------------
    
def get_autodarts_credentials():
    print_header("Autodarts Konfiguration")
    print("Bitte gib deine Autodarts-Zugangsdaten ein.")
    ad_config = {}
    ad_config['AUTODARTS_USER_EMAIL'] = input("    Autodarts E-Mail: ")
    ad_config['AUTODARTS_USER_PASSWORD'] = getpass.getpass("    Autodarts Passwort: ")
    ad_config['AUTODARTS_BOARD_ID'] = input("    Autodarts Board-ID: ")
    return ad_config

#-------------------------------------------------------------------------

def setup_database(db_config):
    # Diese Funktion wird nur für MariaDB aufgerufen
    try:
        python_executable = os.path.join(VENV_DIR, "bin", "python")
        site_packages_cmd = [python_executable, "-c", "import site; print(site.getsitepackages()[0])"]
        site_packages_path = subprocess.check_output(site_packages_cmd, text=True).strip()
        sys.path.append(site_packages_path)
        import mariadb
    except (ImportError, subprocess.CalledProcessError) as e:
        print_error(f"Das 'mariadb'-Paket konnte nicht importiert werden. Fehler: {e}")

    try:
        print(f"Verbinde mit MariaDB auf {db_config['DB_HOST']}...")
        conn = mariadb.connect(
            host=db_config['DB_HOST'], port=int(db_config['DB_PORT']),
            user=db_config['DB_USER'], password=db_config['DB_PASSWORD']
        )
        cursor = conn.cursor()
        print_success("Erfolgreich mit dem MariaDB-Server verbunden.")
        db_name = db_config['DB_DATABASE']
        print(f"Erstelle Datenbank '{db_name}' (falls nicht vorhanden)...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE `{db_name}`;")
        print_success(f"Datenbank '{db_name}' ist bereit.")
        print("Erstelle Tabellen...")
        if not os.path.exists(DB_SCHEMA_FILE):
            print_error(f"Datenbankschema nicht gefunden unter: {DB_SCHEMA_FILE}")
        with open(DB_SCHEMA_FILE, "r") as f:
            sql_script = f.read()
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        conn.commit()
        print_success("Alle Datenbank-Tabellen erfolgreich erstellt.")
    except mariadb.Error as e:
        print_error(f"Ein Datenbankfehler ist aufgetreten: {e}", exit_script=False)
        return False
    finally:
        if 'conn' in locals() and hasattr(conn, 'close'):
            conn.close()
    return True

#-------------------------------------------------------------------------

def save_config(db_type, db_config, ad_config):
    """Speichert die Konfiguration, inklusive des ausgewählten DB-Typs."""
    use_db = (db_type != 'none')
    db_config['DATABASE_TYPE'] = db_type
    
    while True:
        prompt = "Wo sollen die eingegebenen Daten gespeichert werden?\n\rDrücke 1 für .env oder 2 für config.py: "
        choice = input(f"{color.YELLOW}❓ {prompt}{color.END}").strip()
        
        if choice in ['1', '2']:
            break
        else:
            print_error("Ungültige Eingabe. Bitte nur '1' oder '2' eingeben.", exit_script=False)

    if choice == '1':
        # In .env speichern
        with open(ENV_FILE, "w") as f:
            f.write("# Autodarts Credentials\n")
            for key, value in ad_config.items():
                f.write(f"{key}='{value}'\n")
            
            f.write("\n# Database Settings\n")
            f.write(f"USE_DATABASE={str(use_db)}\n")
            f.write(f"DATABASE_TYPE='{db_type}'\n")

            if use_db and db_type == 'mariadb':
                for key, value in db_config.items():
                    if key != 'DATABASE_TYPE': # Wird bereits oben geschrieben
                        f.write(f"{key}='{value}'\n")

        print_success(f"Konfiguration in {ENV_FILE} gespeichert.")

        # ANPASSUNG START: config.py mit Platzhaltern aktualisieren
        try:
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()

            # Platzhalter-Wert
            placeholder = "'siehe .env'"
            
            # Alle Schlüssel, die in .env geschrieben wurden
            keys_to_update = list(ad_config.keys())
            keys_to_update.extend(['USE_DATABASE', 'DATABASE_TYPE', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_DATABASE'])
            if use_db and db_type == 'mariadb':
                keys_to_update.extend([k for k in db_config.keys() if k != 'DATABASE_TYPE' and k != 'DB_PORT'])

            for key in keys_to_update:
                # Regex für 'KEY = "..."' oder 'KEY = '...'' (String-Werte)
                pattern_str = rf"^({key}\s*=\s*)['\"].*?['\"](.*)$"
                content = re.sub(pattern_str, rf"\1{placeholder}\2", content, flags=re.MULTILINE)
                
                # Regex für 'KEY = Wert' (Boolean/None-Werte)
                pattern_bool = rf"^({key}\s*=\s*)\w+(.*)$"
                content = re.sub(pattern_bool, rf"\1{placeholder}\2", content, flags=re.MULTILINE)

            with open(CONFIG_FILE, 'w') as f:
                f.write(content)
            print_info(f"Die config.py wurde mit Platzhaltern aktualisiert, um Verwirrung zu vermeiden.")
        except Exception as e:
            print_warning(f"Konnte config.py nicht mit Platzhaltern aktualisieren: {e}")
        # ANPASSUNG ENDE
    
    else:
        # In config.py speichern
        with open(CONFIG_FILE, 'r') as f: content = f.read()
        
        use_db_str = "True" if use_db else "False"
        pattern_use_db = r"^(USE_DATABASE\s*=\s*)\S+(.*)$"
        replacement_use_db = rf"\1{use_db_str}\2"
        content = re.sub(pattern_use_db, replacement_use_db, content, flags=re.MULTILINE)

        pattern_db_type = r"^(DATABASE_TYPE\s*=\s*)'[^']*'(.*)$"
        replacement_db_type = rf"\1'{db_type}'\2"
        content = re.sub(pattern_db_type, replacement_db_type, content, flags=re.MULTILINE)
        
        for key, value in ad_config.items():
            escaped_value = value.replace('"', '\\"')
            pattern = rf'^({key}\s*=\s*)"[^"]*"(.*)$'
            replacement = rf'\1"{escaped_value}"\2'
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if db_type == 'mariadb':
            for key, value in db_config.items():
                if key == 'DATABASE_TYPE': continue
                escaped_value = str(value).replace("'", "\\'")
                # Universeller Regex für Strings und Zahlen
                pattern = rf"^({key}\s*=\s*)\S+(.*)$"
                # Setze Wert in Anführungszeichen, wenn es ein String ist
                replacement_value = f"'{escaped_value}'" if isinstance(value, str) else str(value)
                replacement = rf"\1{replacement_value}\2"
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE, count=1)

        with open(CONFIG_FILE, 'w') as f: f.write(content)
        print_success(f"Konfiguration in {CONFIG_FILE} gespeichert.")


#-------------------------------------------------------------------------

def ask_db_choice():
    """Fragt den Benutzer nach der gewünschten Datenbankoption."""
    print_header("Datenbank-Auswahl")
    print("Bitte wähle den gewünschten Datenbank-Modus für Langzeit-Statistiken:")
    print("  [1] MariaDB (Externe Datenbank, erfordert zusätzliche System-Pakete)")
    print("  [2] SQLite (Lokale Datei-Datenbank, einfachste Option)")
    print("  [3] Keine Datenbank (Deaktiviert alle Statistiken)")
    
    while True:
        choice = input(f"{color.YELLOW}❓ Wähle (1, 2 oder 3): {color.END}").strip()
        if choice == '1':
            return 'mariadb'
        elif choice == '2':
            return 'sqlite'
        elif choice == '3':
            return 'none'
        else:
            print_error("Ungültige Eingabe. Bitte nur '1', '2' oder '3' eingeben.", exit_script=False)

#-------------------------------------------------------------------------

def setup_user_services(USE_SUDO):
    """Richtet die systemd-Dienste für einen normalen Benutzer ein und startet sie."""
    print_header("Autostart-Konfiguration (Benutzer-Dienste)")
    if not ask_question("Sollen systemd-Benutzer-Dienste für den automatischen Start eingerichtet werden?"):
        return

    user_systemd_dir = os.path.join(os.path.expanduser('~'), '.config', 'systemd', 'user')
    os.makedirs(user_systemd_dir, exist_ok=True)
    backend_service_file = os.path.join(user_systemd_dir, "himues-scoreboard-backend.service")
    frontend_service_file = os.path.join(user_systemd_dir, "himues-scoreboard-frontend.service")

    backend_service_content = f"""
[Unit]
Description=Himues Darts Scoreboard Backend (User Service)
After=network.target

[Service]
WorkingDirectory={BACKEND_DIR}
ExecStart={VENV_DIR}/bin/gunicorn -c gunicorn.conf.py "app_backend:app"
KillSignal=SIGQUIT
KillMode=process-group
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""

    frontend_service_content = f"""
[Unit]
Description=Himues Darts Scoreboard Frontend (User Service)
#BindsTo=himues-scoreboard-backend.service
After=himues-scoreboard-backend.service

[Service]
WorkingDirectory={FRONTEND_DIR}
ExecStart={VENV_DIR}/bin/gunicorn --config config_gunicorn_frontend.py app_frontend:app
KillSignal=SIGQUIT
KillMode=process-group
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
    print("Schreibe Benutzer-Service-Dateien...")
    with open(backend_service_file, "w") as f: f.write(backend_service_content)
    with open(frontend_service_file, "w") as f: f.write(frontend_service_content)
    
    print("Lade & aktiviere Benutzer-Dienste...")
    subprocess.check_call(["systemctl", "--user", "daemon-reload"])
    subprocess.check_call(["systemctl", "--user", "enable", "himues-scoreboard-backend.service"])
    subprocess.check_call(["systemctl", "--user", "enable", "himues-scoreboard-frontend.service"])
    
    print("Starte Benutzer-Dienste...")
    subprocess.check_call(["systemctl", "--user", "start", "himues-scoreboard-backend.service"])
    subprocess.check_call(["systemctl", "--user", "start", "himues-scoreboard-frontend.service"])
    
    print_header("Linger-Modus für Systemstart aktivieren")
    if ask_question("Soll der Linger-Modus aktiviert werden, damit die Dienste beim Systemstart laufen?"):
        user = getpass.getuser()
        print(f"Linger-Modus wird für Benutzer '{user}' aktiviert...")
        command = USE_SUDO + ["loginctl", "enable-linger", user]
        subprocess.check_call(command)
        print_success("Linger-Modus erfolgreich aktiviert!")

#-------------------------------------------------------------------------
    
def setup_system_services():
    """Richtet die systemd-Dienste als System-Dienste ein und startet sie."""
    print_header("Autostart-Konfiguration (System-Dienste)")
    if not ask_question("Sollen systemd-System-Dienste für den automatischen Start eingerichtet werden?"):
        return

    system_systemd_dir = "/etc/systemd/system"
    backend_service_file = os.path.join(system_systemd_dir, "himues-scoreboard-backend.service")
    frontend_service_file = os.path.join(system_systemd_dir, "himues-scoreboard-frontend.service")

    abs_backend_dir = os.path.abspath(BACKEND_DIR)
    abs_frontend_dir = os.path.abspath(FRONTEND_DIR)
    abs_venv_gunicorn = os.path.abspath(os.path.join(VENV_DIR, 'bin', 'gunicorn'))
    run_user = getpass.getuser()

    backend_service_content = f"""
[Unit]
Description=Himues Darts Scoreboard Backend (System Service)
After=network.target

[Service]
User={run_user}
Group={run_user}
WorkingDirectory={abs_backend_dir}
ExecStart={abs_venv_gunicorn} -c gunicorn.conf.py "app_backend:app"
KillSignal=SIGQUIT
KillMode=process-group
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""

    frontend_service_content = f"""
[Unit]
Description=Himues Darts Scoreboard Frontend (System Service)
#BindsTo=himues-scoreboard-backend.service
After=himues-scoreboard-backend.service

[Service]
User={run_user}
Group={run_user}
WorkingDirectory={abs_frontend_dir}
ExecStart={abs_venv_gunicorn} --config config_gunicorn_frontend.py app_frontend:app
KillSignal=SIGQUIT
KillMode=process-group
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    print("Schreibe System-Service-Dateien nach /etc/systemd/system/...")
    with open(backend_service_file, "w") as f: f.write(backend_service_content)
    with open(frontend_service_file, "w") as f: f.write(frontend_service_content)
    
    print("Lade & aktiviere System-Dienste...")
    subprocess.check_call(["systemctl", "daemon-reload"])
    subprocess.check_call(["systemctl", "enable", "himues-scoreboard-backend.service"])
    subprocess.check_call(["systemctl", "enable", "himues-scoreboard-frontend.service"])
    
    print("Starte System-Dienste...")
    subprocess.check_call(["systemctl", "start", "himues-scoreboard-backend.service"])
    subprocess.check_call(["systemctl", "start", "himues-scoreboard-frontend.service"])
    
    print_success("System-Dienste erfolgreich eingerichtet und aktiviert.")

#-------------------------------------------------------------------------
    
def make_scripts_executable():
    """Macht alle .sh-Skripte und das neue Log-Skript ausführbar."""
    print_header("Setze Ausführungsrechte für Skripte")
    script_dirs = [BACKEND_DIR, FRONTEND_DIR, SCRIPT_DIR]
    
    for directory in script_dirs:
        for script_name in ["start-prod.sh", "start-dev.sh", "py-cache-delete.sh"]:
            file_path = os.path.join(directory, script_name)
            if os.path.exists(file_path):
                try:
                    os.chmod(file_path, 0o755)
                    print(f"  {color.GREEN}✅ '{file_path}' wurde ausführbar gemacht.{color.END}")
                except OSError as e:
                    print(f"  {color.RED}❌ Fehler bei '{file_path}': {e}{color.END}")
        
        if directory == SCRIPT_DIR:
            file_path = os.path.join(directory, "show-logs.py")
            if os.path.exists(file_path):
                try:
                    os.chmod(file_path, 0o755)
                    print(f"  {color.GREEN}✅ '{file_path}' wurde ausführbar gemacht.{color.END}")
                except OSError as e:
                    print(f"  {color.RED}❌ Fehler bei '{file_path}': {e}{color.END}")

#-------------------------------------------------------------------------
    
def run_cert_generator_in_venv():
    """Führt die Zertifikats-Erstellung in einem separaten Prozess innerhalb der venv-Umgebung aus."""
    print_header("Starte Zertifikatserstellung in venv-Umgebung")
    python_executable = os.path.join(VENV_DIR, "bin", "python3")
    command_to_run = f"import install; install.generate_and_copy_dummy_certs()"
    
    try:
        subprocess.run(
            [python_executable, "-c", command_to_run],
            check=True,
            cwd=SCRIPT_DIR
        )
        print_success("Zertifikatserstellung erfolgreich abgeschlossen.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_error(f"Fehler bei der Ausführung der Zertifikatserstellung in venv: {e}", exit_script=False)
        print_warning("Die Anwendung könnte ohne SSL-Zertifikate nicht wie erwartet funktionieren.")
        
#-------------------------------------------------------------------------
    
def generate_and_copy_dummy_certs():
    """
    Erzeugt ein selbst-signiertes SSL-Zertifikat und einen privaten Schlüssel
    und kopiert beides in die erforderlichen crt-Verzeichnisse.
    """
    from datetime import datetime, timedelta
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

    print_header("Erzeuge Dummy SSL-Zertifikate")
    try:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"DE"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"NRW"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"DummyCity"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Dummy Org"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"dummy.local"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False)
            .sign(private_key, hashes.SHA256())
        )
        key_bytes = private_key.private_bytes(encoding=Encoding.PEM, format=PrivateFormat.TraditionalOpenSSL, encryption_algorithm=NoEncryption())
        cert_bytes = cert.public_bytes(Encoding.PEM)
        target_dirs = [
            os.path.join(BACKEND_DIR, "crt"),
            os.path.join(FRONTEND_DIR, "crt"),
            os.path.join(SCRIPT_DIR, "frontend_cmd", "crt")
        ]
        for cert_dir in target_dirs:
            os.makedirs(cert_dir, exist_ok=True)
            with open(os.path.join(cert_dir, "dummy.key"), "wb") as f: f.write(key_bytes)
            with open(os.path.join(cert_dir, "dummy.crt"), "wb") as f: f.write(cert_bytes)
            print(f"  {color.GREEN}✅ Zertifikate erfolgreich in '{cert_dir}' erstellt.{color.END}")
    except Exception as e:
        print_error(f"Fehler bei der Erstellung der Dummy-Zertifikate: {e}", exit_script=False)
        print_warning("Die Anwendung könnte ohne SSL-Zertifikate nicht wie erwartet funktionieren.")
        
#-------------------------------------------------------------------------
    
def handle_root_check():
    """Prüft den Benutzerkontext und gibt den sudo-Befehl sowie den Dienst-Typ zurück."""
    if os.geteuid() == 0:
        warning_message = ("ACHTUNG: Sie führen dieses Skript als 'root' aus. Dies wird nicht empfohlen!\n"
                           "Die Anwendung wird als Systemd-Systemdienst installiert und mit root-Rechten laufen.")
        print(f"{color.RED}⚠️  {warning_message}{color.END}")
        if not ask_question("Möchten Sie die Installation trotzdem als root fortsetzen?", default="n"):
            print_error("Installation abgebrochen.", exit_script=True)
        return [], 'system'
    else:
        return ["sudo"], 'user'

#-------------------------------------------------------------------------

def get_local_ips_from_venv():
    """Führt ein Skript in der venv aus, um IPs mit netifaces zu finden."""
    python_executable = os.path.join(VENV_DIR, "bin", "python3")
    script_code = """
import netifaces as ni
import json, sys
local_ips = ['127.0.0.1']
try:
    for interface in ni.interfaces():
        if ni.AF_INET in ni.ifaddresses(interface):
            for link in ni.ifaddresses(interface)[ni.AF_INET]:
                ip = link.get('addr')
                if ip and ip not in local_ips:
                    local_ips.append(ip)
except Exception as e:
    print(f"Error in netifaces subprocess: {e}", file=sys.stderr)
print(json.dumps(sorted(list(set(local_ips)))))
"""
    try:
        result = subprocess.run([python_executable, "-c", script_code], capture_output=True, text=True, check=True, timeout=5)
        if result.stderr:
            print_warning(f"Fehlermeldung vom netifaces-Subprozess:\n{result.stderr}")
        return json.loads(result.stdout.strip())
    except Exception as e:
        print_warning(f"Konnte lokale IP-Adressen nicht mit netifaces ermitteln: {e}")
        return _get_local_ips_fallback()

#-------------------------------------------------------------------------

def _get_local_ips_fallback():
    """Sicherer Fallback zur IP-Ermittlung."""
    local_ips = ['127.0.0.1']
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 80))
        primary_ip = s.getsockname()[0]
        if primary_ip not in local_ips:
            local_ips.append(primary_ip)
        s.close()
    except Exception:
        pass
    return sorted(local_ips)

#-------------------------------------------------------------------------
    
def print_access_info():
    """Liest die Konfigurationen und gibt die Zugriffs-URLs aus."""
    print_header("Zugriffsinformationen")
    
    try:
        from frontend.config_frontend import WEBSERVER_HOST as frontend_host, WEBSERVER_PORT as frontend_port
        from backend.config import WEBSERVER_HOST_IP as backend_host, WEBSERVER_HOST_PORT as backend_port
        
        local_ips = get_local_ips_from_venv()

        print("Das Scoreboard-Frontend sollte unter folgenden Adressen erreichbar sein:")
        if frontend_host == '0.0.0.0':
            for ip in local_ips:
                print(f"  {color.GREEN}➡️  https://{ip}:{frontend_port}{color.END}")
        else:
            print(f"  {color.GREEN}➡️  https://{frontend_host}:{frontend_port}{color.END}")
        
        print("\nDas Backend ist unter folgenden Adressen erreichbar (für Debugging):")
        if backend_host == '0.0.0.0':
            for ip in local_ips:
                print(f"  {color.BLUE}➡️  https://{ip}:{backend_port}/api{color.END}")
        else:
            print(f"  {color.BLUE}➡️  https://{backend_host}:{backend_port}/api{color.END}")

    except Exception as e:
        print_error(f"Fehler beim Ermitteln der Zugriffs-URLs: {e}", exit_script=False)

#-------------------------------------------------------------------------
    
if __name__ == "__main__":
    USE_SUDO, service_type = handle_root_check()
    
    # 1. Allgemeine System-Prüfungen
    check_system()
    check_and_install_venv(USE_SUDO)
    check_and_install_build_tools(USE_SUDO)

    # 2. Grundlegende venv mit Core-Paketen einrichten
    setup_venv()
    run_cert_generator_in_venv()

    # 3. Datenbank-Wahl und bedingte Installation
    # Hauptschleife für die Datenbank-Auswahl
    db_setup_successful = False
    while not db_setup_successful:
        db_type = ask_db_choice()
        db_config = {}

        if db_type == 'sqlite' or db_type == 'none':
            db_setup_successful = True # Diese Optionen können nicht fehlschlagen
        
        elif db_type == 'mariadb':
            if install_mariadb_dependencies(USE_SUDO):
                # Innere Schleife nur für MariaDB-Credential-Versuche
                while True:
                    db_config = get_db_credentials()
                    if setup_database(db_config):
                        db_setup_successful = True
                        break # Erfolg, innere Schleife verlassen
                    else:
                        if not ask_question("Datenbankverbindung fehlgeschlagen. Erneut versuchen?", default="y"):
                            # Benutzer bricht ab, innere Schleife verlassen
                            break 
            else:
                # Abhängigkeiten konnten nicht installiert werden, Hauptschleife wird wiederholt
                print_warning("MariaDB-Abhängigkeiten konnten nicht installiert werden. Bitte wählen Sie eine andere Option.")
                
    # 4. Konfiguration abfragen und speichern
    ad_config = get_autodarts_credentials()
    save_config(db_type, db_config, ad_config)

    # 5. Restliche Installation: Dienste und Zertifikate
    if service_type == 'user':
        setup_user_services(USE_SUDO)
    else:
        setup_system_services()

    make_scripts_executable()
    
     # 6. Starte den interaktiven Log-Viewer
    print_header("Live-Logs werden gestartet...")
    print_info("Drücke 'q', um die Log-Anzeige zu beenden und die Installation abzuschließen.")
    try:
        log_script_path = os.path.join(SCRIPT_DIR, "show-logs.py")
        # Führe das Skript direkt aus, da es jetzt ausführbar ist
        subprocess.run([log_script_path], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_warning(f"Konnte 'show-logs.py' nicht automatisch starten: {e}")
        input("Drücke Enter, um fortzufahren...")
    except Exception as e:
         print_warning(f"Ein unerwarteter Fehler ist beim Starten von 'show-logs.py' aufgetreten: {e}")
         input("Drücke Enter, um fortzufahren...")


    # 7. Abschließende Meldungen
    print_header("Installation abgeschlossen!")

    print("Die Dienste wurden gestartet und sollten jetzt laufen.")
    if service_type == 'user':
        print("Du kannst sie mit 'systemctl --user status ...' überprüfen.")
    else:
        print("Du kannst sie mit 'systemctl status ...' überprüfen.")
    
    print("\nUm die Live-Logs beider Dienste erneut in einer geteilten Ansicht zu sehen, führe aus:")
    print(f"  {color.YELLOW}./show-logs.py{color.END}")
    
    # 8. Zugriffsinformationen ausgeben
    try:
        python_executable = os.path.join(VENV_DIR, "bin", "python")
        site_packages_cmd = [python_executable, "-c", "import site; print(site.getsitepackages()[0])"]
        site_packages_path = subprocess.check_output(site_packages_cmd, text=True).strip()
        sys.path.insert(0, site_packages_path)
        sys.path.insert(0, SCRIPT_DIR)
        
        print_access_info()
    except Exception as e:
        print_warning(f"Konnte Zugriffs-URLs nicht automatisch ermitteln: {e}")