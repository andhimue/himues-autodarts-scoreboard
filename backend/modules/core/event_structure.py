# Backend/modules/core/event_structure.py (Optimierte Version)
from dataclasses import dataclass, asdict, field
from typing import Any, List, Dict, Union

@dataclass
class MatchInfo:
    """ Enthält alle statischen Regeln und Einstellungen, die zu Beginn des Matches festgelegt werden. """
    game_mode:        str           # Der endgültige Spielmodus (z.B. "X01", "Tactics", "Bermuda")
    use_db:           bool = True   # Flag, das die DB-Nutzung an das Frontend meldet

    # Allgemeine Regeln
    legs_to_win:      int = 0       # Anzahl der Legs, die zum Gewinn des Matches benötigt werden.
    sets_to_win:      int = 0       # Anzahl der Sets, die zum Gewinn des Matches benötigt werden.
    max_rounds:       int = 0       # Maximale Anzahl der Runden, bevor ein Leg endet.
    
    # Spezifische Regeln für X01 / Gotcha
    start_score:      int = 0       # Der Start-Punktestand des Spiels (z.B. 501, 301).
    in_mode:          str = None    # Die Regel für den Beginn des Zählens (z.B. "Straight", "Double").
    out_mode:         str = None    # Die Regel für das Beenden eines Legs (z.B. "Straight", "Double").
    
    # Spezifische Regeln für Cricket / Tactics
    scoring_mode:     str = None    # Die Zählweise, z.B. "Normal" oder "Cut Throat". Wird auch für die Segment-Anzeige in ATC "zweckentfremdet"
    targets:          List[str] = field(default_factory=list) # Die Liste der zu treffenden Segmente (z.B. ["20", "19", ...]).
    
    # Spezifische Regeln für ATC / RTW
    order:            str = None    # Die Reihenfolge der zu treffenden Ziele (z.B. "1-20-Bull").
    
    # Spezifische Regeln für ATC
    hits_per_target:  int = 0

    # Spezifische Regeln für Segment Training
    ends_after_type:  str = ""      # Die Bedingung, die das Spiel beendet ("hits" oder "darts").
    ends_after_value: int = 0       # Der numerische Wert für die Endbedingung (z.B. 5 Treffer oder 33 Darts).


@dataclass
class TurnInfo:
    """ Enthält alle dynamischen Daten, die sich von Runde zu Runde oder Wurf zu Wurf ändern. """
    current_round:    int = 1       # Die Nummer der aktuellen Runde im Leg.
    current_leg:      int = 1       # Die Nummer des aktuellen Legs im Set.
    current_set:      int = 1       # Die Nummer des aktuellen Sets im Match.
    
    target:           str = None    # Das spezifische Ziel der aktuellen Runde (z.B. "15" in Shanghai).
    throws:           List[Dict[str, Any]] = field(default_factory=list) # Eine Liste der geworfenen Darts in der aktuellen Aufnahme.
    busted:           bool = False  # Gibt an, ob der Spieler in dieser Aufnahme überworfen hat.


@dataclass
class PlayerInfo:
    """ Enthält den dynamischen Zustand eines einzelnen Spielers. """
    name:             str           # Der Name des Spielers.
    player_type:      str = "guest" # Der Typ des Spielers ("guest", "registered", "owner").
    display_order:    int = None    # Enthält die Reihenfolge der Spieler vom ERSTEN Event eines Spiels. Wird vom Frontend zur Sortierung der Spieleranzeige genutzt
    score:            Union[int, str] = 0  # Der aktuelle Punktestand des Spielers.
    legs_won:         int = 0       # Die Anzahl der vom Spieler gewonnenen Legs.
    sets_won:         int = 0       # Die Anzahl der vom Spieler gewonnenen Sets.
    
    # X01-spezifische Statistiken
    leg_average:      float = 0.0   # Der Average des Spielers im aktuellen Leg.
    match_average:    float = 0.0   # Der Average des Spielers im gesamten Match.
    overall_average:  float = 0.0   # Der historische Gesamt-Average des Spielers aus der Datenbank für X01.

    # Cricket-spezifische Statistiken
    mpr:              float = 0.0   # "Marks Per Round", die Statistik für Cricket.
    overall_mpr:      float = 0.0   # Der historische Gesamt-MPR des Spielers (cricket, tactics).
    hits:             Dict[str, int] = field(default_factory=dict) # Ein Dictionary, das die Anzahl der Treffer pro Zielsegment speichert.
    
    # ATC/CountUp/Segment Training-spezifische Statistiken
    current_target:   str = None    # Das persönliche, als nächstes zu treffende Ziel des Spielers (z.B. in ATC).
    overall_hit_rate: float = 0.0   # Der historische Gesamt-Hit-Rate des Spielers (around the clock).
    match_hit_rate:   float = 0.0   # Die Trefferquote des Spielers im gesamten Match.
    leg_hit_rate:     float = 0.0   # Die Trefferquote des Spielers im aktuellen Leg.
    darts_thrown_leg: int = 0       # Die Anzahl der vom Spieler im aktuellen Leg geworfenen Darts.

    # CountUp-spezifische Statistiken
    overall_ppr:      float = 0.0   # NEU: Der historische Gesamt-PPR.


@dataclass
class GameEvent:
    """ Der Haupt-Container für alle Events an das Frontend. """
    event:            str           # Der Typ des Events, z.B. "match-started" oder "game-update".
    game_state:       str           # Der aktuelle Zustand des Spiels, z.B. "throw", "busted", "leg_won".
    
    match:            MatchInfo     # Ein Objekt, das die statischen Regeln des Matches enthält.
    turn:             TurnInfo      # Ein Objekt, das die dynamischen Daten der aktuellen Runde enthält.
    players:          List[PlayerInfo] # Eine Liste mit den Zustandsobjekten aller Spieler.
    
    current_player_index: int       # Der Index des Spielers in der `players`-Liste, der aktuell am Zug ist.
    
    # Optionale Felder, die nur bei Bedarf gefüllt werden
    winner_info:      Dict[str, Any] = field(default_factory=dict)       # Enthält Informationen über den Gewinner, wenn ein Leg/Match endet.
    checkout_guide:   List[Dict[str, Any]] = field(default_factory=list) # Eine Liste mit Checkout-Vorschlägen für X01.


    def to_dict(self):
        """ Wandelt das Event-Objekt in ein Dictionary um, damit es als JSON gesendet werden kann. """
        from dataclasses import asdict
        return asdict(self)