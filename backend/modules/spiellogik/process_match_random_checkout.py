# Backend/modules/spiellogik/process_match_random_checkout.py

from ..core.utils_backend import log_function_call
from ..core import constants as c
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event

@log_function_call
def process_match_random_checkout(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Random Checkout'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit den spezifischen Regeln für diesen Modus:
    1. Setzt die korrekte MatchInfo (z.B. outMode, maxRounds).
    2. Überschreibt die Standard-Gewinner-Logik für den Fall, dass das
       Rundenlimit erreicht wird. In diesem Szenario gewinnt der Spieler mit
       dem niedrigsten verbleibenden Punktestand.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event    = create_universal_game_event(live_game_data)

    # Random Checkout-spezifische MatchInfo erstellen und zuweisen
    settings = live_game_data.get(c.KEY_SETTINGS, {})
    event.match = MatchInfo(
        game_mode  = "Random Checkout",
        out_mode   = settings.get(c.KEY_OUTMODE),
        max_rounds = settings.get(c.KEY_MAX_ROUNDS, 0)
    )

    # Spezifische Gewinner-Logik für Rundenlimit anwenden
    # Die Standard-Logik für einen normalen Checkout-Sieg ist im Helfer bereits korrekt.
    # Wir müssen nur den Sonderfall "Rundenlimit erreicht" überschreiben.
    if live_game_data.get(c.KEY_WINNER, -1) != -1:
        # Spielende durch Rundenlimit
        event.game_state = c.STATE_LEG_WON
        # Der Spieler mit dem NIEDRIGSTEN Score gewinnt
        winner_player = min(event.players, key=lambda p: p.score)
        event.winner_info = {c.KEY_PLAYER: winner_player.name, 'type': 'Leg'}


    return event.to_dict()