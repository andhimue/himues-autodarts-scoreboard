# Backend/modules/core/utils_backend.py

import collections
import functools
import inspect
import json
import logging
import os
import psutil
import pprint
import sys
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme

from . import shared_state as g


# einen "Decorator" erstellen
# Ein Decorator ist eine Funktion, die eine andere Funktion "einhüllt", um ihr vor oder nach der Ausführung zusätzliches Verhalten hinzuzufügen.
# Das ist perfekt, um wiederkehrenden Code wie Ihre Logging-Zeile zu vermeiden.
def log_function_call(func):
    """
    Ein Decorator, der den Aufruf einer Funktion loggt,
    wenn der globale Debug-Modus aktiv ist.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        # 1. Die Logging-Aktion, die vor der Funktion ausgeführt wird
        if g.DEBUG > 1:
            # func.__name__ ist der saubere Weg, den Namen der Funktion zu bekommen
            log_event(f"Funktionsaufruf: {func.__name__}")
        
        # 2. Die ursprüngliche Funktion ausführen und ihr Ergebnis zurückgeben
        return func(*args, **kwargs)
        
    # 3. Die "eingehüllte" Funktion zurückgeben
    return wrapper
    


#----------------------------------------------------

def log_event(title, data=None):
    """
    Fügt einen Eintrag zum Debug-Log hinzu und sendet ihn an die Debug-Webseite.
    """
   
   
    if not hasattr(g, 'debug_log'):
        g.debug_log = []

    if title == 'clear_log':
        g.socketio.emit('clear_log', namespace='/debug')

    else:
        log_entry = {
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "title": title,
            # Wende hier die rekursive Sortierung an
            "data": get_sorted_dict(data) if data else None
        }
        g.debug_log.append(log_entry)

        # Sende das Update an alle verbundenen Debug-Clients
        if g.socketio:
            g.socketio.emit('log_update', log_entry, namespace='/debug')

#----------------------------------------------------

def log_event_ad(title, data=None):
    """
    Fügt einen Eintrag zum Autodarts-Debug-Log hinzu und sortiert den
    inneren 'data'-Teil für eine bessere Lesbarkeit.
    """
    if not hasattr(g, 'ad_debug_log'):
        g.ad_debug_log = []

    if title == 'clear_log':
        g.ad_debug_log.clear()

        if g.socketio:
            g.socketio.emit('clear_log', namespace='/debugad')

        return # Wichtig: Funktion hier beenden

    # Wir erstellen eine bearbeitbare Kopie der Daten
    processed_data = data.copy() if isinstance(data, dict) else data

    # Prüfe, ob ein inneres 'data'-Objekt existiert und sortiere es
    if isinstance(processed_data, dict) and 'data' in processed_data:
        inner_data = processed_data.get('data', {})

        # Die Sortierung wird nur auf das verschachtelte 'data'-Objekt angewendet
        processed_data['data'] = get_sorted_dict(inner_data)

    # Erstelle einen besseren Titel für die Anzeige
    event_type = data.get('data', {}).get('event', 'state') # Holt 'start', 'finish' oder 'state'
    log_title  = f"{data.get('channel')} - {event_type}"

    log_entry = {
        "time":  datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "title": log_title,
        "data":  processed_data # Verwende die teil-sortierten Daten
    }

    # An das korrekte Log-Array anhängen
    g.ad_debug_log.append(log_entry)

    # Sende das Update an alle verbundenen Debug-Clients
    if g.socketio:
        g.socketio.emit('log_update', log_entry, namespace='/debugad')

#----------------------------------------------------

@log_function_call
def broadcast(data):
    """
    Sendet ein Event an alle verbundenen Frontend-Clients (Scoreboard).
    Protokolliert das Event und filtert leere/ungültige Game-Events,
    um ein ungewolltes Zurücksetzen des Frontends zu verhindern.
    """
    event_name = data.get("event")
    if not event_name:
        return

    # --- Filter gegen leere/ungültige Events ---
    # Prüfe, ob das Event Spielerdaten enthalten sollte, aber nicht tut.
    # Ein 'match-ended' Event darf explizit leer sein, um das Frontend zurückzusetzen.
    # {'event': 'Board Status', 'data': {'status': 'Board Started'}}
    # {'event': 'Board Status', 'data': {'status': 'Manual reset'}}
    # würden dazu führen, dass die Frontendanzeige zurückgesetzt wird und daher hier ausgefiltert
    if event_name != 'match-ended' and not data.get('players'):
        if g.DEBUG > 0:
            logging.warning(f"Senden von leerem Event '{event_name}' unterdrückt, um Frontend-Reset zu verhindern.", stack_info=True)
            logging.warning(data)
            return # Sendevorgang hier abbrechen
    # --- Ende des Filters ---

    # Event für das Debug-Log protokollieren
    log_event(f"Event gesendet: '{event_name}'", data)

    if g.socketio:
        g.socketio.emit(event_name, data)
        
#----------------------------------------------------

@log_function_call
def unicast(sid, data):
    """Sendet ein Event an einen einzelnen Client."""
    event_name = data.get("event")

    if not event_name:
        return

    if g.socketio:
        g.socketio.emit(event_name, data, room=sid)

#----------------------------------------------------

@log_function_call
def reset_checkouts_counter():
    """
    Setzt den Zähler für Checkout-Versuche zurück.
    """
    g.checkoutsCounter = {}

#----------------------------------------------------

@log_function_call
def get_executable_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

    elif __file__:
        return os.path.dirname(os.path.realpath(__file__))

    else:
        raise RuntimeError("Unable to determine executable directory.")

#----------------------------------------------------

@log_function_call
def check_already_running():
    max_count = 2
    count = 0
    me, extension = os.path.splitext(os.path.basename(sys.argv[0]))
    logging.info("Process is %s", me)
    for proc in psutil.process_iter(['pid', 'name']):
        proc_name = proc.info['name'].lower()
        proc_name, extension = os.path.splitext(proc_name)

        if proc_name == me:
            count += 1

            if count >= max_count:
                logging.info("%s is already running. Exit", me)
            return True
    return False # False zurückgeben, wenn alles ok ist

#----------------------------------------------------

def write_json_to_file(datei, modus, data, formated=True, SeparatorLine=None):
    """
    Eine robuste Funktion zum Schreiben von JSON-Dateien,
    die Fehler abfängt und eine explizite Debug-Ausgabe erzeugt.
    """
    file_path = os.path.join(g.BACKEND_DIR, datei)

    try:
        with open(datei, modus) as f:
            if formated:
                json.dump(data, f, indent=4)
                if SeparatorLine:
                    f.write(SeparatorLine)

            else:
                json.dump(data, f)
                if SeparatorLine:
                    f.write(SeparatorLine)

            f.write('\n')
            

    except Exception as e:
        # Wenn irgendein Fehler auftritt, wird er hier abgefangen und ausgegeben.
        sys.stderr.write(f"[FEHLER] Konnte nicht in Datei schreiben: {datei}\n")
        sys.stderr.write(f"Fehlergrund: {e}\n")
        sys.stderr.flush()

#----------------------------------------------------

def get_sorted_dict(d):
    """
    Sortiert die oberste Ebene eines Dictionaries.
    - Zuerst nach dem Typ des Werts (einfache Typen vor komplexen).
    - Danach alphabetisch nach dem Schlüssel.
    """
    if not isinstance(d, dict):
        return d

    # 1. Definiere die Reihenfolge der Typen. Niedrigere Zahlen kommen zuerst.
    # Wir fassen alle "einfachen" Typen in einer Gruppe (0) zusammen.
    type_order = {
        str:        0,
        int:        0,
        float:      0,
        bool:       0,
        type(None): 0,
        list:       1,
        dict:       2
    }

    # 2. Sortiere die Dictionary-Einträge.
    # Der `key`-Parameter von sorted() erhält für jeden Eintrag ein Tupel, z.B. (0, 'event').
    # Python sortiert zuerst nach dem ersten Element des Tupels (der Typ-Gruppe)
    # und bei Gleichheit nach dem zweiten Element (dem alphabetischen Schlüssel).
    sorted_items = sorted(
        d.items(),
        key=lambda item: (type_order.get(type(item[1]), 99), item[0])
    )

    # 3. Baue aus den sortierten Einträgen ein neues Dictionary auf.
    return dict(sorted_items)
    
#----------------------------------------------------

def setup_logger():
    """
    Konfiguriert das Logging für die gesamte Anwendung.
    
    Setzt ein Standard-Level für die eigenen App-Logs und unterdrückt gleichzeitig
    zu gesprächige INFO-Meldungen von Drittanbieter-Bibliotheken, indem deren
    Loglevel gezielt auf WARNING gesetzt wird.
    """
    # Das Format und der Handler bleiben gleich
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

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
    g.logger = logging.getLogger("Backend") # Ein spezifischer Name für deine eigenen App-Logs