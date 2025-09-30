# Backend/modules/spiellogik/process_match_rtw.py

from ..core.utils_backend import log_function_call
from ..core import constants as c
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event

@log_function_call
def process_match_rtw(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Round the World'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit den RTW-spezifischen Daten:
    1. Setzt die korrekte MatchInfo mit der Spielreihenfolge ('order').
    2. Ermittelt das Zielsegment für die aktuelle Runde und trägt es ein.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event    = create_universal_game_event(live_game_data)

    # RTW-spezifische MatchInfo erstellen und zuweisen
    settings = live_game_data.get(c.KEY_SETTINGS, {})
    event.match = MatchInfo(
        game_mode = "RTW",
        order     = settings.get(c.KEY_ORDER, "1-20-Bull")
    )

    # 3. RTW-spezifisches Runden-Ziel ermitteln und eintragen
    targets_list  = live_game_data.get(c.KEY_STATE, {}).get(c.KEY_TARGETS, [])
    current_round = event.turn.current_round
    target_number = '?'

    if 0 < current_round <= len(targets_list):
        target_obj = targets_list[current_round - 1]
        number     = target_obj.get('number')

        if number is not None:
            target_number = c.TARGET_BULL if number == 25 else str(number)

    event.turn.target = target_number

    # Überschreibe den Spielzustand, falls nötig
    # Da Segment Training immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"

    return event.to_dict()