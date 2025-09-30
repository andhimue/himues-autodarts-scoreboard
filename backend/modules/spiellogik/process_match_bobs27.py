# Backend/modules/spiellogik/process_match_bobs27.py

from ..core.utils_backend import log_function_call
from ..core.event_structure import MatchInfo
from ..core import constants as c
from .match_handler import create_universal_game_event

@log_function_call
def process_match_bobs27(live_game_data):
    """Verarbeitet ein Live-Update für ein 'Bob's 27'-Spiel.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit den spezifischen Regeln für diesen Modus:
    1. Setzt die korrekte MatchInfo mit den Regeln für Bob's 27.
    2. Ermittelt das korrekte Doppel-Ziel für die aktuelle Runde.
    3. Überschreibt die Standard-Zustandslogik, um die spezifischen
       Endbedingungen 'busted' (Punkte unter 1) und 'game_over'
       (alle Runden gespielt) abzubilden.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event = create_universal_game_event(live_game_data)

    # Bob's 27-spezifische MatchInfo erstellen und zuweisen
    settings = live_game_data.get(c.KEY_SETTINGS, {})
    event.match = MatchInfo(
        game_mode    = "Bob's 27",
        scoring_mode = settings.get(c.KEY_MODE, "Normal"),
        order        = settings.get(c.KEY_ORDER, "1-20-Bull"),
        max_rounds   = 21 # Inklusive Bull
    )

    # Spezifisches Runden-Ziel ermitteln
    current_round = event.turn.current_round
    target = "Game Over"

    # Das D vor dem Ziel hinzufügen (bei Bob's 27 wird immer auf Doppelfelder geworfen)
    if current_round <= 20:
        target = f"D{current_round}"

    # Wenn "1-20-Bull" gespielt wird ist das letzte Ziel das Bullseye (der Server leifert "Bull" (einzelfeld) das wird hier angepasst)
    elif current_round == 21 and c.TARGET_BULL in event.match.order:
        target = c.TARGET_BULLSEYE # D25

    event.turn.target = target

    # Spezifische Logik für das Spielende
    turn_data = live_game_data.get(c.KEY_TURNS, [{}])[0]
    max_rounds_played = 21 if c.TARGET_BULL in event.match.order else 20
    
    if turn_data.get(c.STATE_BUSTED, False):
        event.game_state = c.STATE_BUSTED

    elif live_game_data.get(c.STATE_GAME_FINISHED, False) or current_round > max_rounds_played:
        event.game_state = c.STATE_GAME_OVER

    # Überschreibe den Spielzustand, falls nötig
    # Da Bobs 27 immer nur ein Leg ist, behandeln wir einen Match-Gewinn
    # immer als Leg-Gewinn für eine konsistente Anzeige.
    if event.game_state == c.STATE_MATCH_WON:
        event.game_state = c.STATE_LEG_WON
        if event.winner_info:
            event.winner_info["type"] = "Leg"

    return event.to_dict()