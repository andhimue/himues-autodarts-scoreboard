# =============================================================================
# === Windows Installations-Skript für Himues Darts Scoreboard              ===
# =============================================================================
#
# Dieses Skript automatisiert die vollständige Installation des Scoreboards
# unter Windows 10/11. Es prüft und installiert alle notwendigen Abhängigkeiten,
# richtet die virtuelle Python-Umgebung ein, konfiguriert die Anwendung und
# erstellt Windows-Dienste für den automatischen Start.
#
# Ausführung: Rechtsklick auf die Datei -> "Mit PowerShell ausführen"
#
# =============================================================================

# --- Skript-Konfiguration ---
$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$VenvDir = Join-Path $ScriptDir "venv"
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"
$ConfigFile = Join-Path $BackendDir "config.py"
$EnvFile = Join-Path $BackendDir ".env"
$DbSchemaFile = Join-Path $BackendDir "docs" "database_schema.sql"
$NssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
$NssmZipFile = Join-Path $ScriptDir "nssm.zip"
$NssmExePath = Join-Path $ScriptDir "nssm-2.24" "win64" "nssm.exe"

# --- Admin-Rechte prüfen und anfordern ---
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Administratorrechte sind für die Installation erforderlich. Starte das Skript neu als Admin..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoExit", "-File", "`"$($MyInvocation.MyCommand.Path)`""
    exit
}

# --- Hilfsfunktionen für farbige Ausgabe ---
function Write-Header { param($Message) Write-Host "`n--- $($Message) ---" -ForegroundColor Magenta -BackgroundColor Black }
function Write-Success { param($Message) Write-Host "✅ $($Message)" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "⚠️  $($Message)" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $($Message)" -ForegroundColor Red; exit 1 }
function Ask-Question {
    param([string]$Prompt, [string]$Default = "y")
    $options = if ($Default -eq "y") { "[Y/n]" } else { "[y/N]" }
    $answer = Read-Host "❓ $($Prompt) $($options)"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $Default -eq "y" }
    return $answer.ToLower().StartsWith('y')
}

# --- Abhängigkeits-Prüfungen ---

#region Abhängigkeiten

function Check-And-Install-Dependencies {
    Write-Header "Prüfe System-Voraussetzungen..."

    # Python 3.8+
    $pythonVersion = (python --version 2>&1)
    if ($LASTEXITCODE -ne 0 -or -not ($pythonVersion -match "Python 3\.(8|9|1[0-9])")) {
        Write-Warning "Python 3.8+ nicht gefunden. Versuch der Installation via winget..."
        if (Ask-Question "Soll Python 3.11 installiert werden?") {
            try { winget install -e --id Python.Python.3.11 } catch { Write-Error "Installation von Python fehlgeschlagen. Bitte manuell installieren." }
            Write-Warning "Bitte schließen Sie dieses Fenster, öffnen Sie ein neues PowerShell (Admin)-Fenster und starten Sie das Skript erneut."
            Read-Host "Drücken Sie Enter, um das Skript zu beenden."
            exit
        } else { Write-Error "Python ist für die Installation erforderlich." }
    } else { Write-Success "Python-Version ist ausreichend ($($pythonVersion))." }

    # Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Warning "Git nicht gefunden. Versuch der Installation via winget..."
        if (Ask-Question "Soll Git installiert werden?") {
            try { winget install -e --id Git.Git } catch { Write-Error "Installation von Git fehlgeschlagen. Bitte manuell installieren." }
        } else { Write-Error "Git wird für den Betrieb benötigt." }
    } else { Write-Success "Git ist installiert." }

    # MariaDB C Connector
    $connectorPath = "C:\Program Files\MariaDB\MariaDB Connector C 64-bit\include\mysql.h"
    if (-not (Test-Path $connectorPath)) {
        Write-Warning "MariaDB C Connector nicht gefunden. Dieser ist für die Datenbank-Anbindung notwendig."
        if (Ask-Question "Soll der MariaDB C Connector jetzt heruntergeladen und installiert werden?") {
            $connectorUrl = "https://archive.mariadb.org/c-connector/3.3.8/mariadb-connector-c-3.3.8-win64.msi"
            $msiPath = Join-Path $env:TEMP "mariadb-connector.msi"
            Write-Host "Lade Connector herunter..."
            Invoke-WebRequest -Uri $connectorUrl -OutFile $msiPath
            Write-Host "Starte Connector-Installation. Bitte folgen Sie den Anweisungen..."
            Start-Process msiexec.exe -ArgumentList "/i `"$($msiPath)`"" -Wait
            Remove-Item $msiPath
            Write-Success "MariaDB C Connector-Installation abgeschlossen."
        } else { Write-Warning "Installation ohne Datenbank-Support fortgesetzt. Statistiken sind nicht verfügbar." }
    } else { Write-Success "MariaDB C Connector gefunden." }
    
    Write-Success "Alle System-Voraussetzungen sind erfüllt."
}

function Install-NSSM {
    if (-not (Test-Path $NssmExePath)) {
        Write-Header "Installiere Service Manager (NSSM)"
        Write-Host "Lade NSSM herunter..."
        Invoke-WebRequest -Uri $NssmUrl -OutFile $NssmZipFile
        Write-Host "Entpacke NSSM..."
        Expand-Archive -Path $NssmZipFile -DestinationPath $ScriptDir -Force
        Remove-Item $NssmZipFile
        Write-Success "NSSM erfolgreich eingerichtet."
    } else {
        Write-Success "Service Manager (NSSM) ist bereits vorhanden."
    }
}

#endregion Abhängigkeiten

# --- Kern-Installationslogik ---

#region Installation

function Setup-Venv {
    Write-Header "Virtuelle Umgebung (venv) einrichten"
    if (Test-Path $VenvDir) {
        Write-Success "Virtuelle Umgebung existiert bereits."
    } else {
        Write-Host "Erstelle virtuelle Umgebung..."
        python -m venv $VenvDir
        Write-Success "Virtuelle Umgebung erfolgreich erstellt."
    }

    Write-Host "Installiere Abhängigkeiten aus requirements.txt..."
    $pipExe = Join-Path $VenvDir "Scripts" "pip.exe"
    try {
        & $pipExe install -r $RequirementsFile
        Write-Success "Alle Abhängigkeiten erfolgreich installiert."
    } catch {
        Write-Error "Fehler bei der Installation der Python-Abhängigkeiten."
    }
}

function Configure-Application {
    $useDb = $false
    $dbConfig = @{}
    
    if (Ask-Question "Möchtest du die MariaDB-Datenbank für Langzeit-Statistiken verwenden?") {
        Write-Header "Datenbank-Konfiguration"
        $dbConfig.DB_HOST = Read-Host "  Datenbank-Host [localhost]" -Prompt "  Datenbank-Host"
        if ([string]::IsNullOrWhiteSpace($dbConfig.DB_HOST)) { $dbConfig.DB_HOST = "localhost" }

        $dbConfig.DB_PORT = Read-Host "  Datenbank-Port [3306]" -Prompt "  Datenbank-Port"
        if ([string]::IsNullOrWhiteSpace($dbConfig.DB_PORT)) { $dbConfig.DB_PORT = "3306" }

        $dbConfig.DB_USER = Read-Host "  Datenbank-Benutzer" -Prompt "  Datenbank-Benutzer"
        $dbConfig.DB_PASSWORD = Read-Host "  Datenbank-Passwort" -AsSecureString | ForEach-Object { [System.Net.NetworkCredential]::new('', $_).Password }
        $dbConfig.DB_DATABASE = Read-Host "  Name für die neue Darts-Datenbank [himues_darts_db]" -Prompt "  Name der Datenbank"
        if ([string]::IsNullOrWhiteSpace($dbConfig.DB_DATABASE)) { $dbConfig.DB_DATABASE = "himues_darts_db" }

        # Konvertiere Hashtabelle zu JSON für die Übergabe an das Python-Hilfsskript
        $dbConfigJson = $dbConfig | ConvertTo-Json -Compress
        
        $pythonExe = Join-Path $VenvDir "Scripts" "python.exe"
        $dbSetupScriptPath = Join-Path $ScriptDir "windows_setup_database.py"

        try {
            # Führe das Python-Skript aus, um die Datenbank einzurichten
            & $pythonExe $dbSetupScriptPath -dbConfig $dbConfigJson -schemaFile $DbSchemaFile
            Write-Success "Datenbank erfolgreich eingerichtet."
            $useDb = $true
        } catch {
            Write-Warning "Datenbank-Setup fehlgeschlagen. DB-Nutzung wird deaktiviert. Fehler: $($_.Exception.Message)"
            $useDb = $false
        }
    }

    Write-Header "Autodarts Konfiguration"
    $adConfig = @{}
    $adConfig.AUTODARTS_USER_EMAIL = Read-Host "  Autodarts E-Mail" -Prompt "  Autodarts E-Mail"
    $adConfig.AUTODARTS_USER_PASSWORD = Read-Host "  Autodarts Passwort" -AsSecureString | ForEach-Object { [System.Net.NetworkCredential]::new('', $_).Password }
    $adConfig.AUTODARTS_BOARD_ID = Read-Host "  Autodarts Board-ID" -Prompt "  Autodarts Board-ID"

    # Speichere Konfiguration
    $choice = Read-Host "Wo sollen die Daten gespeichert werden? (1 für .env, 2 für config.py)"
    if ($choice -eq "1") {
        $envContent = @(
            "# Autodarts Credentials",
            "AUTODARTS_USER_EMAIL='$($adConfig.AUTODARTS_USER_EMAIL)'",
            "AUTODARTS_USER_PASSWORD='$($adConfig.AUTODARTS_USER_PASSWORD)'",
            "AUTODARTS_BOARD_ID='$($adConfig.AUTODARTS_BOARD_ID)'"
        )
        if ($useDb) {
            $envContent += @(
                "",
                "# Database Credentials",
                "DB_HOST='$($dbConfig.DB_HOST)'",
                "DB_PORT='$($dbConfig.DB_PORT)'",
                "DB_USER='$($dbConfig.DB_USER)'",
                "DB_PASSWORD='$($dbConfig.DB_PASSWORD)'",
                "DB_DATABASE='$($dbConfig.DB_DATABASE)'"
            )
        }
        Set-Content -Path $EnvFile -Value $envContent
        Write-Success "Konfiguration in $EnvFile gespeichert."
    } else {
        $content = Get-Content $ConfigFile -Raw
        $content = $content -replace "(USE_DATABASE\s*=\s*)\w+", "`$1$($useDb.ToString())"
        foreach ($key in $adConfig.Keys) {
            $content = $content -replace "($($key)\s*=\s*"").*?(\"")", "`$1$($adConfig[$key])`$2"
        }
        if ($useDb) {
            foreach ($key in $dbConfig.Keys) {
                 $content = $content -replace "($($key)\s*=\s*').*?(')", "`$1$($dbConfig[$key])`$2"
            }
        }
        Set-Content -Path $ConfigFile -Value $content
        Write-Success "Konfiguration in $ConfigFile gespeichert."
    }
}

function Generate-And-Copy-Certs {
    Write-Header "Erzeuge Dummy SSL-Zertifikate"
    $pythonExe = Join-Path $VenvDir "Scripts" "python.exe"
    $certScript = @'
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import os

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"DE"),
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

target_dirs = [os.path.join(BACKEND_DIR, "crt"), os.path.join(FRONTEND_DIR, "crt")]
for cert_dir in target_dirs:
    os.makedirs(cert_dir, exist_ok=True)
    with open(os.path.join(cert_dir, "dummy.key"), "wb") as f: f.write(key_bytes)
    with open(os.path.join(cert_dir, "dummy.crt"), "wb") as f: f.write(cert_bytes)
    print(f"Zertifikate erfolgreich in '{cert_dir}' erstellt.")
'@
    $certScript | & $pythonExe -
    Write-Success "Zertifikatserstellung abgeschlossen."
}

function Setup-Services {
    Write-Header "Windows-Dienste einrichten"
    if (-not (Ask-Question "Sollen Windows-Dienste für den automatischen Start eingerichtet werden?")) { return }

    $gunicornPath = Join-Path $VenvDir "Scripts" "gunicorn.exe"
    
    # Backend Service
    $backendServiceName = "HimuesScoreboardBackend"
    Write-Host "Erstelle Backend-Dienst: $backendServiceName"
    & $NssmExePath install $backendServiceName $gunicornPath ('-c gunicorn.conf.py "app_backend:app"')
    & $NssmExePath set $backendServiceName AppDirectory $BackendDir
    & $NssmExePath set $backendServiceName AppStopMethodSkip 6
    & $NssmExePath set $backendServiceName AppRestartDelay 3000
    
    # Frontend Service
    $frontendServiceName = "HimuesScoreboardFrontend"
    Write-Host "Erstelle Frontend-Dienst: $frontendServiceName"
    & $NssmExePath install $frontendServiceName $gunicornPath ('--config config_gunicorn_frontend.py app_frontend:app')
    & $NssmExePath set $frontendServiceName AppDirectory $FrontendDir
    & $NssmExePath set $frontendServiceName AppStopMethodSkip 6
    & $NssmExePath set $frontendServiceName AppRestartDelay 3000
    & $NssmExePath set $frontendServiceName DependOnService $backendServiceName

    Write-Success "Dienste erfolgreich erstellt."
}

#endregion Installation

# --- Haupt-Skriptablauf ---
try {
    Check-And-Install-Dependencies
    Install-NSSM
    Setup-Venv
    Configure-Application
    Generate-And-Copy-Certs
    Setup-Services

    Write-Header "Installation abgeschlossen!"
    Write-Host "Die Dienste wurden eingerichtet. Sie können sie über die 'Dienste'-App oder per Befehl starten:" -ForegroundColor Cyan
    Write-Host "  sc start HimuesScoreboardBackend" -ForegroundColor Cyan
    Write-Host "  sc start HimuesScoreboardFrontend" -ForegroundColor Cyan
    Write-Host "Nach einem Neustart des Systems werden die Dienste automatisch gestartet." -ForegroundColor Cyan

} catch {
    Write-Error "Ein unerwarteter Fehler ist aufgetreten: $($_.Exception.Message)"
}

Read-Host "Drücken Sie Enter, um das Fenster zu schließen."
