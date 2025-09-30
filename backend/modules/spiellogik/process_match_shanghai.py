# Backend/modules/spiellogik/process_match_shanghai.py

from ..core.utils_backend import log_function_call
from ..core import constants as c
from .match_handler import create_universal_game_event

@log_function_call
def process_match_shanghai(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Shanghai'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    ergänzt dieses anschließend um die Shanghai-spezifische Information,
    welches Zahlensegment in der aktuellen Runde das Ziel ist.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event   = create_universal_game_event(live_game_data)

    # Shanghai-Sonderlogik: Das Runden-Ziel ermitteln und eintragen
    targets = live_game_data.get(c.KEY_STATE, {}).get(c.KEY_TARGETS, [])
    current_round = event.turn.current_round
    
    if 0 < current_round <= len(targets):
        target_number = targets[current_round - 1]
        event.turn.target = str(target_number)

    else:
        event.turn.target = 'N/A'

    # Überschreibe den Spielzustand, falls nötig
    # Da Shanghai immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"


    return event.to_dict()