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
        return
    print_warning("Die MariaDB-Entwicklungsdateien (Connector/C) scheinen zu fehlen.")
    try:
        subprocess.check_call(["which", "apt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print_error("apt-Paketmanager nicht gefunden. Bitte installiere 'libmariadb-dev' manuell.")
    if not ask_question("Soll versucht werden, das Paket 'libmariadb-dev' automatisch zu installieren?"):
        print_error("Installation abgebrochen. Bitte installiere 'libmariadb-dev' manuell.")
    try:
        package_name = "libmariadb-dev"
        print(f"Versuche, das Paket '{package_name}' zu installieren...")
        print_warning("Für die Installation wird dein administratives Passwort (sudo) benötigt.")
        subprocess.check_call(USE_SUDO + ["apt", "install", "-y", package_name])
        print_success(f"'{package_name}' wurde erfolgreich installiert.")
    except Exception as e:
        print_error(f"Installation von '{package_name}' fehlgeschlagen: {e}")

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
    print_header("Virtuelle Umgebung (venv) einrichten")
    if os.path.exists(VENV_DIR):
        print_success("Virtuelle Umgebung existiert bereits.")
    else:
        print("Erstelle virtuelle Umgebung...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
        print_success("Virtuelle Umgebung erfolgreich erstellt.")

    print("Installiere Abhängigkeiten aus requirements.txt...")
    pip_executable = os.path.join(VENV_DIR, "bin", "pip")
    try:
        subprocess.check_call([pip_executable, "install", "-r", REQUIREMENTS_FILE])
        print_success("Alle Abhängigkeiten erfolgreich installiert.")
    except subprocess.CalledProcessError as e:
        print_error(f"Fehler bei der Installation der Abhängigkeiten: {e}")
    except FileNotFoundError:
        print_error(f"Datei nicht gefunden: {REQUIREMENTS_FILE}. Stelle sicher, dass sie existiert.")

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
    try:
        sys.path.append(os.path.join(VENV_DIR, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"))
        import mariadb
    except ImportError:
        print_error("Das 'mariadb'-Paket konnte nicht importiert werden. Bitte stelle sicher, dass die venv-Installation erfolgreich war.")

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
        if 'conn' in locals() and not conn._closed:
            conn.close()
    return True

#-------------------------------------------------------------------------
    
def save_config(use_db, db_config, ad_config):
    """Fragt den Benutzer nach dem Speicherort und validiert die Eingabe auf '1' oder '2'."""
    while True:
        prompt = "Wo sollen die eingegebenen Daten gespeichert werden?\n\rDrücke 1 für .env oder 2 für config.py: "
        choice = input(f"{color.YELLOW}❓ {prompt}{color.END}").strip()
        
        if choice in ['1', '2']:
            break  # Verlässt die Schleife bei gültiger Eingabe
        else:
            print_error("Ungültige Eingabe. Bitte nur '1' oder '2' eingeben.", exit_script=False)

    # Logik für .env
    if choice == '1':
        with open(ENV_FILE, "w") as f:
            f.write("# Autodarts Credentials\n")
            for key, value in ad_config.items():
                f.write(f"{key}='{value}'\n")
            if use_db:
                f.write("\n# Database Credentials\n")
                for key, value in db_config.items():
                    f.write(f"{key}='{value}'\n")
        print_success(f"Konfiguration in {ENV_FILE} gespeichert.")
    
    # Logik für config.py
    else: # choice ist garantiert '2'
        with open(CONFIG_FILE, 'r') as f: content = f.read()
        
        content = re.sub(r"USE_DATABASE\s*=\s*\w+", f"USE_DATABASE = {str(use_db)}", content)
        
        for key, value in ad_config.items():
            content = re.sub(f"{key}\s*=\s*\".*\"", f"{key} = \"{value}\"", content)
        if use_db:
            for key, value in db_config.items():
                content = re.sub(f"{key}\s*=\s*'.*'", f"{key} = '{value}'", content, 1)
        with open(CONFIG_FILE, 'w') as f: f.write(content)
        print_success(f"Konfiguration in {CONFIG_FILE} gespeichert.")
    
#-------------------------------------------------------------------------
    
def configure_application():
    db_config = {}
    use_db = ask_question("Möchtest du die MariaDB-Datenbank für Langzeit-Statistiken verwenden?")
    if use_db:
        db_config = get_db_credentials()
        if not setup_database(db_config):
            use_db = False
            print_warning("Datenbank-Setup fehlgeschlagen. DB-Nutzung wird deaktiviert.")
    ad_config = get_autodarts_credentials()
    save_config(use_db, db_config, ad_config)

#-------------------------------------------------------------------------

def setup_user_services(USE_SUDO):
    """Richtet die systemd-Dienste für einen normalen Benutzer ein."""
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
BindsTo=himues-scoreboard-backend.service
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
    
    print_header("Linger-Modus für Systemstart aktivieren")
    if ask_question("Soll der Linger-Modus aktiviert werden, damit die Dienste beim Systemstart laufen?"):
        user = getpass.getuser()
        print(f"Linger-Modus wird für Benutzer '{user}' aktiviert...")
        command = USE_SUDO + ["loginctl", "enable-linger", user]
        subprocess.check_call(command)
        print_success("Linger-Modus erfolgreich aktiviert!")

#-------------------------------------------------------------------------
    
def setup_system_services():
    """Richtet die systemd-Dienste als System-Dienste ein (wenn als root ausgeführt)."""
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
BindsTo=himues-scoreboard-backend.service
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
    print_success("System-Dienste erfolgreich eingerichtet und aktiviert.")

#-------------------------------------------------------------------------
    
def make_scripts_executable():
    """Macht alle .sh-Skripte in den frontend- und backend-Verzeichnissen ausführbar."""
    print_header("Setze Ausführungsrechte für Shell-Skripte")
    script_dirs = [BACKEND_DIR, FRONTEND_DIR]
    script_files = ["start-prod.sh", "start-dev.sh", "py-cache-delete.sh"]
    
    for directory in script_dirs:
        for script_name in script_files:
            file_path = os.path.join(directory, script_name)
            if os.path.exists(file_path):
                try:
                    # Setzt die Rechte auf 755 (rwxr-xr-x)
                    os.chmod(file_path, 0o755)
                    print(f"  {color.GREEN}✅ '{file_path}' wurde ausführbar gemacht.{color.END}")
                except OSError as e:
                    print(f"  {color.RED}❌ Fehler bei '{file_path}': {e}{color.END}")

#-------------------------------------------------------------------------
    
def run_cert_generator_in_venv():
    """
    Führt die Zertifikats-Erstellung in einem separaten Prozess
    innerhalb der venv-Umgebung aus, um auf installierte Pakete zugreifen zu können.
    """
    print_header("Starte Zertifikatserstellung in venv-Umgebung")
    
    # Pfad zum Python-Interpreter in der venv
    python_executable = os.path.join(VENV_DIR, "bin", "python3")

    # Der Befehl, der ausgeführt werden soll:
    # "import install; install.generate_and_copy_dummy_certs()"
    # Dies importiert das Skript selbst als Modul und ruft die Funktion auf.
    command_to_run = f"import install; install.generate_and_copy_dummy_certs()"
    
    try:
        # Führe den Befehl mit dem venv-Python-Interpreter aus
        subprocess.run(
            [python_executable, "-c", command_to_run],
            check=True,
            cwd=SCRIPT_DIR  # Stelle sicher, dass das Skript im richtigen Verzeichnis läuft
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
        # 1. Privaten Schlüssel generieren
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 2. Selbst-signiertes Zertifikat erstellen
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
            .not_valid_after(datetime.utcnow() + timedelta(days=3650)) # 10 Jahre gültig
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False)
            .sign(private_key, hashes.SHA256())
        )

        # 3. Schlüssel und Zertifikat in Bytes umwandeln
        key_bytes = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )
        cert_bytes = cert.public_bytes(Encoding.PEM)

        # 4. In alle Zielverzeichnisse schreiben
        target_dirs = [
            os.path.join(BACKEND_DIR, "crt"),
            os.path.join(FRONTEND_DIR, "crt"),
            os.path.join(SCRIPT_DIR, "frontend_cmd", "crt")
        ]

        for cert_dir in target_dirs:
            os.makedirs(cert_dir, exist_ok=True)
            key_path = os.path.join(cert_dir, "dummy.key")
            cert_path = os.path.join(cert_dir, "dummy.crt")
            
            with open(key_path, "wb") as f:
                f.write(key_bytes)
            with open(cert_path, "wb") as f:
                f.write(cert_bytes)
            print(f"  {color.GREEN}✅ Zertifikate erfolgreich in '{cert_dir}' erstellt.{color.END}")

    except Exception as e:
        print_error(f"Fehler bei der Erstellung der Dummy-Zertifikate: {e}", exit_script=False)
        print_warning("Die Anwendung könnte ohne SSL-Zertifikate nicht wie erwartet funktionieren.")
        
#-------------------------------------------------------------------------
    
def handle_root_check():
    """
    Prüft den Benutzerkontext, gibt eine Warnung aus und gibt den sudo-Befehl
    sowie den Dienst-Typ ('user' oder 'system') zurück.
    """
    if os.geteuid() == 0:
        warning_message = (
            "ACHTUNG: Sie führen dieses Skript als 'root' aus. Dies wird nicht empfohlen!\n"
            "Die Anwendung wird als Systemd-Systemdienst installiert und mit root-Rechten laufen."
        )
        print(f"{color.RED}⚠️  {warning_message}{color.END}")
        
        if not ask_question("Möchten Sie die Installation trotzdem als root fortsetzen?", default="n"):
            print_error("Installation abgebrochen.", exit_script=True)
        
        return [], 'system'  # Leere Liste für sudo, Typ 'system'
    else:
        return ["sudo"], 'user' # "sudo" in Liste, Typ 'user'

#-------------------------------------------------------------------------

def get_local_ips_from_venv():
    """
    Führt ein minimales Python-Skript in der venv-Umgebung aus, das netifaces
    nutzt, um alle IPs zu finden und als JSON auf der Konsole ausgibt.
    Diese Ausgabe wird hier aufgefangen und als Python-Liste zurückgegeben.
    """
    python_executable = os.path.join(VENV_DIR, "bin", "python3")
    
    # Das Python-Skript, das der Subprozess ausführen soll, als reiner Text.
    # Es ist komplett eigenständig und hat keine Abhängigkeiten zu install.py.
    script_code = """
import netifaces as ni
import json
import sys

local_ips = ['127.0.0.1']
try:
    for interface in ni.interfaces():
        if ni.AF_INET in ni.ifaddresses(interface):
            for link in ni.ifaddresses(interface)[ni.AF_INET]:
                ip = link.get('addr')
                if ip and ip not in local_ips:
                    local_ips.append(ip)
except Exception as e:
    # Schreibe eventuelle Fehler auf den Fehlerkanal, damit wir sie sehen können
    print(f"Error in netifaces subprocess: {e}", file=sys.stderr)

# Gib das Ergebnis als JSON-String auf dem Erfolgskanal aus
print(json.dumps(sorted(list(set(local_ips)))))
"""
    
    try:
        result = subprocess.run(
            [python_executable, "-c", script_code], # Führe den Text-String direkt aus
            capture_output=True, text=True, check=True, timeout=5
        )
        # Wenn der Subprozess Fehler meldet, zeigen wir sie als Warnung an
        if result.stderr:
            print_warning(f"Fehlermeldung vom netifaces-Subprozess:\n{result.stderr}")

        # Wandle den aufgefangenen JSON-String wieder in eine Python-Liste um
        return json.loads(result.stdout.strip())
    except Exception as e:
        # Fängt Fehler ab, z.B. wenn der Subprozess abstürzt oder 'netifaces' nicht da ist
        print_warning(f"Konnte lokale IP-Adressen nicht mit netifaces ermitteln: {e}")
        # Fällt auf die alte, zuverlässige "Dummy Socket"-Methode zurück
        return _get_local_ips_fallback()

#-------------------------------------------------------------------------

def _get_local_ips_fallback():
    """
    Ein sicherer Fallback, der die primäre IP-Adresse über lokale Systemaufrufe ermittelt,
    falls die netifaces-Methode fehlschlägt.
    """
    local_ips = ['127.0.0.1']
    try:
        # 1. Hostnamen des Systems ermitteln
        hostname = socket.gethostname()
        # 2. IP-Adresse für diesen Hostnamen lokal auflösen
        primary_ip = socket.gethostbyname(hostname)
        
        if primary_ip not in local_ips:
            local_ips.append(primary_ip)
    except Exception:
        # Fehler (z.B. Hostname kann nicht aufgelöst werden) werden ignoriert,
        # '127.0.0.1' bleibt als Minimum erhalten.
        pass
    return sorted(local_ips)

#-------------------------------------------------------------------------
def _get_config_values(file_path):
    """Liest spezifische Host- und Port-Werte aus einer Konfigurationsdatei."""
    host, port, disable_https = None, None, False
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            # Regex zum Suchen von FLASK_HOST oder WEBSERVER_HOST_IP
            host_match = re.search(r'(FLASK_HOST|WEBSERVER_HOST_IP)\s*=\s*[\'"]?([^\'"]+)', content)
            if host_match:
                host = host_match.group(2).strip()
            
            # Regex zum Suchen von FLASK_PORT oder WEBSERVER_HOST_PORT
            port_match = re.search(r'(FLASK_PORT|WEBSERVER_HOST_PORT)\s*=\s*[\'"]?(\d+)', content)
            if port_match:
                port = port_match.group(2).strip()

            # Regex zum Suchen von HTTPS-Deaktivierung
            https_match = re.search(r'(WEBSERVER_DISABLE_HTTPS|WEBSERVER_DISABLE_HTTPS_FRONTEND)\s*=\s*(True|False)', content)
            if https_match:
                disable_https = https_match.group(2).strip() == 'True'

    except Exception as e:
        print_warning(f"Fehler beim Lesen der Konfiguration aus {file_path}: {e}")
    
    return host, port, disable_https

#-------------------------------------------------------------------------
def print_access_info():
    """
    Ermittelt die Host-IPs und Ports aus den Konfigurationsdateien und gibt die Zugriffs-URLs aus.
    """
    print_header("Zugriffsinformationen")
    
    # Backend-Konfiguration laden
    backend_config_path = os.path.join(BACKEND_DIR, "config.py")
    backend_host, backend_port, backend_disable_https = _get_config_values(backend_config_path)
    
    # Frontend-Konfiguration laden
    frontend_config_path = os.path.join(FRONTEND_DIR, "config_frontend.py")
    frontend_host, frontend_port, frontend_disable_https = _get_config_values(frontend_config_path)

    # Fallback-Werte, falls das Auslesen fehlschlägt
    backend_host = backend_host or '0.0.0.0'
    backend_port = backend_port or '6001'
    frontend_host = frontend_host or '0.0.0.0'
    frontend_port = frontend_port or '6002'

    # Protokoll bestimmen
    backend_protocol = "http" if backend_disable_https else "https"
    frontend_protocol = "http" if frontend_disable_https else "https"

    try:
        # Ruft alle möglichen IPs ab (wird nur verwendet, wenn Host = 0.0.0.0)
        all_local_ips = get_local_ips_from_venv()

        # --- FRONTEND IP-Filter-Logik ---
        if frontend_host == '0.0.0.0':
            # Regel 1: Bei 0.0.0.0 werden alle IPs angezeigt
            frontend_display_ips = all_local_ips
        elif frontend_host == '127.0.0.1':
            # Regel 2: Bei 127.0.0.1 wird nur diese angezeigt
            frontend_display_ips = ['127.0.0.1']
        else:
            # Regel 3: Bei jeder anderen IP wird nur diese angezeigt
            frontend_display_ips = [frontend_host]

        print("Das Scoreboard-Frontend sollte unter folgenden Adressen erreichbar sein:")
        for ip in frontend_display_ips:
            print(f"  {color.GREEN}➡️  {frontend_protocol}://{ip}:{frontend_port}{color.END}")

        # --- BACKEND IP-Filter-Logik ---
        if backend_host == '0.0.0.0':
            # Regel 1: Bei 0.0.0.0 werden alle IPs angezeigt
            backend_display_ips = all_local_ips
        elif backend_host == '127.0.0.1':
            # Regel 2: Bei 127.0.0.1 wird nur diese angezeigt
            backend_display_ips = ['127.0.0.1']
        else:
            # Regel 3: Bei jeder anderen IP wird nur diese angezeigt
            backend_display_ips = [backend_host]
        
        print("\nDas Backend ist unter folgenden Adressen erreichbar (für Debugging):")
        for ip in backend_display_ips:
            print(f"  {color.BLUE}➡️  {backend_protocol}://{ip}:{backend_port}/api{color.END}")

    except Exception as e:
        print_error(f"Fehler beim Ermitteln der Zugriffs-URLs: {e}", exit_script=False)

#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
    
if __name__ == "__main__":
    USE_SUDO, service_type = handle_root_check()
 
    print_header("Prüfe System-Voraussetzungen...")
    check_and_install_venv(USE_SUDO)
    check_and_install_mariadb_dev(USE_SUDO)
    check_and_install_build_tools(USE_SUDO)
    print_success("Alle System-Voraussetzungen sind erfüllt.")
    
    check_system()
    setup_venv()
    configure_application()

     # Entscheide hier, welche Funktion aufgerufen wird
    if service_type == 'user':
        setup_user_services(USE_SUDO)
    else: # service_type ist 'system'
        setup_system_services()

    make_scripts_executable()
    run_cert_generator_in_venv()
    
    print_header("Installation abgeschlossen!")

    if service_type == 'user':
        print("Du kannst die Dienste nun mit: \n\r  systemctl --user start himues-scoreboard-backend\n\r  systemctl --user start himues-scoreboard-frontend\n\r starten oder das System neu booten.")
    else: # service_type ist 'system'
        print("Du kannst die Dienste nun mit: \n\r  systemctl start himues-scoreboard-backend\n\r  systemctl start himues-scoreboard-frontend\n\r starten oder das System neu booten.\n\r")
    
    print_access_info()    
