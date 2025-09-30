# Backend/modules/spiellogik/process_match_bull_off.py

from ..core.utils_backend import log_function_call
from ..core.event_structure import MatchInfo
from .match_handler import create_universal_game_event
from ..core import constants as c
from ..core import shared_state as g

@log_function_call
def process_match_bull_off(live_game_data):
    """Verarbeitet ein Live-Update für die 'Bull-off'-Phase.

    Ruft die universelle Hilfsfunktion zur Erstellung des GameEvents auf und
    modifiziert dieses anschließend mit der spezifischen Logik für das Ausbullen:
    1. Setzt die korrekte MatchInfo für den "Bull-off"-Modus.
    2. Formatiert den Punktestand der Spieler (zeigt '-' statt 0 an).
    3. Implementiert die spezielle Logik zur Zustandsermittlung, die prüft, ob
       alle Spieler geworfen haben, um dann einen Sieger oder ein Unentschieden
       festzustellen.

    Args:
        live_game_data (dict): Der vollständige Live-Spielzustand vom
                               Autodarts-WebSocket.

    Returns:
        dict: Ein Dictionary, das das standardisierte und modifizierte
              `GameEvent`-Objekt repräsentiert.
    """
    # Universelles Event-Objekt erstellen lassen
    event       = create_universal_game_event(live_game_data)

    # Bull-off-spezifische MatchInfo erstellen und zuweisen
    event.match = MatchInfo(game_mode="Bull-off")

    # Spieler-Scores für die Anzeige anpassen
    for player in event.players:
        if player.score == 0:
            player.score = "-"

    # Spezifische Logik für Spielzustand und Gewinner
    num_players    = len(event.players)
    players_thrown = 0
    stats_list     = live_game_data.get(c.KEY_STATS, [])

    # Zählen, wie viele Spieler bereits geworfen haben
    for i in range(num_players):
        if i < len(stats_list) and stats_list[i].get(c.KEY_LEG_STATS, {}).get('coords') is not None:
            players_thrown += 1

    # Prüfen, ob das Ausbullen beendet ist
    if players_thrown == num_players:
        # Bull-off ist vorbei. Setze die Anzeigereihenfolge für alle Spieler zurück.
        # Dies signalisiert dem nächsten Event, eine neue Reihenfolge zu "latchen".
        for player_name in g.player_data_map:
            g.player_data_map[player_name][c.KEY_DISPLAY_ORDER] = None

        winner_index = live_game_data.get(c.KEY_GAME_WINNER, -1)

        if winner_index != -1:
            # Es gibt einen Gewinner
            event.game_state = c.STATE_LEG_WON
            winner_name = live_game_data.get(c.KEY_PLAYERS, [])[winner_index].get('name', '')
            event.winner_info = {c.KEY_PLAYER: winner_name, 'type': 'Bull-off'}

            # Setze den aktiven Spieler-Index auf den Gewinner für die Anzeige
            event.current_player_index = winner_index
            
            # Den Gewinner des Ausbullens merken
            g.bull_off_winner = winner_name
            
        else:
            # Es ist ein Unentschieden
            event.game_state = "bull_off_tie"
            g.bull_off_winner = None # Sicherstellen, dass bei Unentschieden zurückgesetzt wird

    return event.to_dict()