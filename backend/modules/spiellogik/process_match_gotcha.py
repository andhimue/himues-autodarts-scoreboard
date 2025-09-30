# Backend/modules/spiellogik/process_match_gotcha.py

from ..core.utils_backend import log_function_call
from ..core import constants as c
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event

@log_function_call
def process_match_gotcha(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Gotcha'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    überschreibt anschließend die generische MatchInfo mit den spezifischen
    Regeln für den Gotcha-Modus.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event = create_universal_game_event(live_game_data)

    # Gotcha-spezifische MatchInfo erstellen und zuweisen
    settings = live_game_data.get(c.KEY_SETTINGS, {})
    event.match = MatchInfo(
        game_mode="Gotcha",
        start_score=settings.get(c.KEY_TARGET_SCORE, 0),
        out_mode=settings.get(c.KEY_OUTMODE),
        max_rounds=settings.get(c.KEY_MAX_ROUNDS, 0)
    )

    # Überschreibe den Spielzustand, falls nötig
    # Da Gotcha immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"

    return event.to_dict()