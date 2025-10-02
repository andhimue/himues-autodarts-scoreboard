# Frontend/modules/core/config_loader_frontend.py

import os
import sys
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
    g.FLASK_HOST                       = os.getenv("FLASK_HOST", getattr(config, 'FLASK_HOST', '0.0.0.0'))
    g.FLASK_DEBUG                      = _to_bool(os.getenv("FLASK_DEBUG", getattr(config, 'FLASK_DEBUG', False)))
    flask_port                         = os.getenv("FLASK_PORT", getattr(config, 'FLASK_PORT', 6002))

    # Sichere Umwandlung für FLASK_PORT
    port_value = os.getenv("FLASK_PORT", getattr(config, 'FLASK_PORT', 6002))
    try:
        g.FLASK_PORT = int(flask_port)
    except (ValueError, TypeError):
        g.FLASK_PORT = 6002 # Sicherer Standardwert
        
    g.SERVER_ADDRESS                   = os.getenv("SERVER_ADDRESS", getattr(config, 'SERVER_ADDRESS', "127.0.0.1:6001"))
    g.WEBSERVER_DISABLE_HTTPS_FRONTEND = _to_bool(os.getenv("WEBSERVER_DISABLE_HTTPS_FRONTEND", getattr(config, 'WEBSERVER_DISABLE_HTTPS_FRONTEND', False)))

    g.DEBUG                            = _to_bool(os.getenv("DEBUG", getattr(config, 'DEBUG', 0)))

    g.SHOW_ONLY_FIREWORK_VIDEO         = _to_bool(os.getenv("SHOW_ONLY_FIREWORK_VIDEO", getattr(config, 'SHOW_ONLY_FIREWORK_VIDEO', False)))
    g.FORCE_STABLE_SORTING             = _to_bool(os.getenv("FORCE_STABLE_SORTING", getattr(config, 'FORCE_STABLE_SORTING', True)))
    g.SHOW_PLAYER_CARD                 = _to_bool(os.getenv("SHOW_PLAYER_CARD", getattr(config, 'SHOW_PLAYER_CARD', False)))

    # Für Listen ist getattr die beste Methode, da sie nicht einfach aus .env geladen werden können
    g.BROWSER_NAMES_TO_SHOW_ONLY_VIDEO = getattr(config, 'BROWSER_NAMES_TO_SHOW_ONLY_VIDEO', ["Tizen 5.0"])