# frontend/utils.py
import pprint
import traceback
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme
import sys

from . import shared_state_frontend as g


def setup_logger():
    """
    Konfiguriert das Logging für die gesamte Anwendung.
    
    Setzt ein Standard-Level für die eigenen App-Logs und unterdrückt gleichzeitig
    zu gesprächige INFO-Meldungen von Drittanbieter-Bibliotheken, indem deren
    Loglevel gezielt auf WARNING gesetzt wird.
    """
    # Das Format und der Handler bleiben gleich
    log_format = '%(asctime)s - %(name)s - %(levelname)-8s - %(message)s'

    # ================================================================
    # SCHRITT 1: Eigenes Theme für die Farben definieren
    # ================================================================
    custom_theme = Theme({
        "logging.level.info": "yellow",           # INFO-Meldungen in Cyan
        "logging.level.warning": "cyan",        # WARNING-Meldungen in Gelb
        "logging.level.error": "bold red",        # ERROR-Meldungen in fettem Rot
        "logging.level.critical": "bold white on red" # CRITICAL in weiß auf rotem Grund
        # DEBUG behält die Standardfarbe
    })
    
    # ================================================================
    # SCHRITT 2: Console-Objekt mit dem eigenen Theme erstellen
    # ================================================================
    force_console = Console(
        force_terminal=True, # Erzwingt Farben, auch unter Gunicorn
        theme=custom_theme   # Wendet unser benutzerdefiniertes Theme an
    )

    # Schritt 3 Konfiguriere den Root Logger. Wir setzen ihn auf das niedrigste Level,
    #    das wir in unserer App sehen wollen (z.B. DEBUG).
    log_level = logging.DEBUG if g.DEBUG > 0 else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # SCHRITT 4: RichHandler mit der benutzerdefinierten Console initialisieren
    rich_handler = RichHandler(
        rich_tracebacks=True,
        console=force_console
    )
    
    # Füge den neuen Handler zum Root Logger hinzu.
    root_logger.addHandler(rich_handler)

    # Schritt 5 Bring die "gesprächigen" Bibliotheken zum Schweigen.
    # Wir holen uns ihre Logger und setzen ihr Level manuell auf ERROR.
    # Damit werden ihre INFO- und DEBUG-Meldungen unterdrückt.
    logging.getLogger('engineio.server').setLevel(logging.ERROR)
    logging.getLogger('socketio.server').setLevel(logging.ERROR)
    logging.getLogger('geventwebsocket.handler').setLevel(logging.ERROR)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # Schritt 6. Hole einen spezifischen Logger für deine eigenen App-Nachrichten.
    # Das hilft, deine eigenen Logs im Output zu erkennen.
    g.logger = logging.getLogger("Frontend") # Ein spezifischer Name für deine eigenen App-Logs