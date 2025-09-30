# Backend/modules/spiellogik/process_match_bermuda.py

from ..core.utils_backend import log_function_call
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event
from ..core import constants as c

@log_function_call
def process_match_bermuda(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Bermuda'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit den Bermuda-spezifischen Regeln:
    1. Setzt die korrekten Match-Regeln (z.B. max_rounds=13).
    2. Ermittelt das Runden-Ziel (z.B. "15", "Double", "Bullseye").
    3. Überschreibt die Standard-Gewinner-Logik, da bei Bermuda am Ende der
       Spieler mit der höchsten Punktzahl gewinnt.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event = create_universal_game_event(live_game_data)

    # MatchInfo mit Bermuda-spezifischen Regeln überschreiben
    event.match = MatchInfo(
        game_mode="Bermuda",
        max_rounds=13
    )

    # Runden-Ziel ermitteln und eintragen
    current_round       = event.turn.current_round
    target_display      = "Game Over"
    targets_from_server = live_game_data.get(c.KEY_STATE, {}).get(c.KEY_TARGETS, [])

    if 0 < current_round <= len(targets_from_server):
        target_obj = targets_from_server[current_round - 1]
        bed        = target_obj.get('bed')
        number     = target_obj.get('number', 0)

        if bed == c.TARGET_SINGLE and number > 0:
            target_display = str(number)

        elif bed == c.TARGET_DOUBLE and number == 25:
            target_display = c.TARGET_BULLSEYE

        elif bed == c.TARGET_DOUBLE:
            target_display = c.TARGET_DOUBLE

        elif bed == c.TARGET_TRIPLE:
            target_display =c.TARGET_TRIPLE

        elif bed == c.TARGET_SINGLE and number == 25:
            target_display = c.TARGET_BULL
    
    event.turn.target = target_display

    # Überschreibe den Spielzustand, falls nötig
    # Da Shanghai immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"



    return event.to_dict()