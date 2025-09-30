# Backend/modules/core/config_loader.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import argparse

from . import shared_state as g
import config

def load_and_parse_config():
    """
    Lädt die Konfiguration in einer klaren Hierarchie und speichert sie im globalen
    shared_state (g).

    Lade-Reihenfolge:
    1. Standardwerte aus der config.py.
    2. Geheime/Umgebungsspezifische Werte aus der .env-Datei (überschreiben die Standards).
    """
    # 1. Lade Konfiguration aus der .env Datei
    if hasattr(sys, "_MEIPASS"):
        env_path = Path(sys._MEIPASS) / ".env/.env"
    else:
        env_path = Path(".env")
    load_dotenv(dotenv_path=env_path)

    g.AUTODARTS_USER_EMAIL            = os.getenv("AUTODARTS_USER_EMAIL")             or getattr(config, 'AUTODARTS_USER_EMAIL', g.AUTODARTS_USER_EMAIL)
    g.AUTODARTS_USER_PASSWORD         = os.getenv("AUTODARTS_USER_PASSWORD")          or getattr(config, 'AUTODARTS_USER_PASSWORD', g.AUTODARTS_USER_PASSWORD)
    g.AUTODARTS_BOARD_ID              = os.getenv("AUTODARTS_BOARD_ID")               or getattr(config, 'AUTODARTS_BOARD_ID', g.AUTODARTS_BOARD_ID)
    g.AUTODARTS_CERT_CHECK            =                                                  getattr(config, 'AUTODARTS_CERT_CHECK', g.AUTODARTS_CERT_CHECK)

    g.USE_DATABASE                    = _to_bool(getattr(config, 'USE_DATABASE', g.USE_DATABASE))
    g.DB_USER                         =     os.getenv("DB_USER")                      or getattr(config, 'DB_USER', g.DB_USER)
    g.DB_PASSWORD                     =     os.getenv("DB_PASSWORD")                  or getattr(config, 'DB_PASSWORD', g.DB_PASSWORD)
    g.DB_HOST                         =     os.getenv("DB_HOST")                      or getattr(config, 'DB_HOST', g.DB_HOST)
    g.DB_DATABASE                     =     os.getenv("DB_DATABASE")                  or getattr(config, 'DB_DATABASE', g.DB_DATABASE)
    port_value                        =     os.getenv("DB_PORT")                      or getattr(config, 'DB_PORT', g.DB_PORT)

    # Versuche, den Wert in eine Ganzzahl umzuwandeln.
    # Bei einem Fehler (z.B. bei leerem String) wird der Standardwert 3306 verwendet.
    try:
        g.DB_PORT = int(port_value)
    except (ValueError, TypeError):
        g.DB_PORT = 3306
        
    g.DEBUG                           = _to_bool(                                        getattr(config, 'DEBUG', g.DEBUG))
    
    g.X01_DISPLAY_MODE                =                                                  getattr(config, 'X01_DISPLAY_MODE', 'cards')

    g.WEBSERVER_DISABLE_HTTPS         = _to_bool(                                        getattr(config, 'WEBSERVER_DISABLE_HTTPS', g.WEBSERVER_DISABLE_HTTPS))
    g.WEBSERVER_HOST_IP               =                                                  getattr(config, 'WEBSERVER_HOST_IP', g.WEBSERVER_HOST_IP)
    webserver_host_port               =                                                  getattr(config, 'WEBSERVER_HOST_PORT', g.WEBSERVER_HOST_PORT)
    
    # Versuche, den Wert in eine Ganzzahl umzuwandeln.
    # Bei einem Fehler (z.B. bei leerem String) wird der Standardwert 3306 verwendet.
    try:
        g.WEBSERVER_HOST_PORT = int(webserver_host_port)
    except (ValueError, TypeError):
        g.WEBSERVER_HOST_PORT = 6001
#-----------------------------------------------------

#os.getenv() liefert imemr einen String zurück. Beide folgende Beipiele liefern also den String "True"
# X = True
# X = "True"
# haben als ergebnis immer den String "True" und nicht den Boolean True
# Eine Hilfsfunktion, die den Inhalt des Strings prüft
def _to_bool(value):
    return str(value).lower() in ('true', '1', 't', 'y', 'yes')
