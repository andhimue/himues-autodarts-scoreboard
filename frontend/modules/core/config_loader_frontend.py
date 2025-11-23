# Frontend/modules/core/config_loader_frontend.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Importiere die Frontend-spezifischen Module
from . import shared_state_frontend as g
import config_frontend as config

def _to_bool(value):
    """Eine Hilfsfunktion, die verschiedene String-Repräsentationen in einen Boolean umwandelt."""
    # Prüft, ob der Wert überhaupt existiert, bevor lower() aufgerufen wird
    return str(value).lower() in ('true', '1', 't', 'y', 'yes') if value is not None else False

def load_and_parse_config_frontend():
    """
    Lädt die Frontend-Konfiguration in einer klaren Hierarchie und speichert sie
    im globalen shared_state (g).

    Lade-Reihenfolge:
    1. Standardwerte direkt hier im Code als Fallback.
    2. Werte aus der config_frontend.py.
    3. Umgebungsspezifische Werte aus einer .env-Datei (überschreiben alles).
    """
    # Lade Konfiguration aus der .env Datei (optional)
    env_path = Path(".env")
    load_dotenv(dotenv_path=env_path)

    # Lese Werte und befülle das globale g-Objekt mit klarer Fallback-Logik
    g.CERT_FILE                       =                                                  getattr(config, 'CERT_FILE', g.CERT_FILE)
    g.KEY_FILE                        =                                                  getattr(config, 'KEY_FILE', g.KEY_FILE)

    g.SHOW_MATCH_DURATION             = _to_bool(os.getenv("SHOW_MATCH_DURATION",        getattr(config, 'SHOW_MATCH_DURATION', True)))
    g.SHOW_DURATION_IN_GAMERULES      = _to_bool(os.getenv("SHOW_DURATION_IN_GAMERULES", getattr(config, 'SHOW_DURATION_IN_GAMERULES', False)))
    g.MATCH_DURATION_INTERVAL         = os.getenv("MATCH_DURATION_INTERVAL",             getattr(config, 'MATCH_DURATION_INTERVAL', False))

    g.CONFIG_EDITOR_USER              = os.getenv("CONFIG_EDITOR_USER",                  getattr(config, 'CONFIG_EDITOR_USER', 'admin'))
    g.CONFIG_EDITOR_PASSWORD          = os.getenv("CONFIG_EDITOR_PASSWORD",              getattr(config, 'CONFIG_EDITOR_PASSWORD', 'admin'))
    
    g.WEBSERVER_HOST                  = os.getenv("WEBSERVER_HOST_HOST",                 getattr(config, 'WEBSERVER_HOST_HOST', '0.0.0.0'))
    webserver_port                    = os.getenv("WEBSERVER_PORT",                      getattr(config, 'WEBSERVER_PORT', 6002))

    g.BACKEND_HOST                    = os.getenv("BACKEND_HOST",                        getattr(config, 'BACKEND_HOST', '127.0.0.1'))
    backend_port                      = os.getenv("BACKEND_PORT",                        getattr(config, 'BACKEND_PORT', 6001))

    # Sichere Umwandlung für Ports
    try:
        g.WEBSERVER_PORT = int(webserver_port)
    except (ValueError, TypeError):
        g.WEBSERVER_PORT = 6002 # Sicherer Standardwert

    try:
        g.BACKEND_PORT = int(backend_port)
    except (ValueError, TypeError):
        g.BACKEND_PORT = 6001 # Sicherer Standardwert

    g.DEBUG                            = _to_bool(os.getenv("DEBUG",                     getattr(config, 'DEBUG', 0)))

    g.SHOW_ONLY_FIREWORK_VIDEO         = _to_bool(os.getenv("SHOW_ONLY_FIREWORK_VIDEO",  getattr(config, 'SHOW_ONLY_FIREWORK_VIDEO', False)))
    g.FORCE_STABLE_SORTING             = _to_bool(os.getenv("FORCE_STABLE_SORTING",      getattr(config, 'FORCE_STABLE_SORTING', True)))
    g.SHOW_PLAYER_CARD                 = _to_bool(os.getenv("SHOW_PLAYER_CARD",          getattr(config, 'SHOW_PLAYER_CARD', False)))

    # Für Listen ist getattr die beste Methode, da sie nicht einfach aus .env geladen werden können
    g.BROWSER_NAMES_TO_SHOW_ONLY_VIDEO =                                                 getattr(config, 'BROWSER_NAMES_TO_SHOW_ONLY_VIDEO', ["Tizen 5.0"])

    # Lade die Ignore-Liste für die Satisic-Anzeige
    g.STATS_IGNORE_PLAYERS             = getattr(config, 'STATS_IGNORE_PLAYERS', [])