# Backend/modules/core/constants.py

# Event-Namen
EVT_GAME_UPDATE   = "game-update"
EVT_MATCH_STARTED = "match-started"
EVT_MATCH_ENDED   = "match-ended"
EVT_BOARD         = "board"
EVT_WELCOME       = "welcome"
EVT_LOBBY         = "lobby"

# WebSocket Kanäle
AUTODARTS_MATCHES = "autodarts.matches"
AUTODARTS_BOARDS  = "autodarts.boards"
AUTODARTS_USERS   = "autodarts.users"
AUTODARTS_LOBBIES = "autodarts.lobbies"

# WebSocket Typen
TYPE_SUBSCRIBE    = "subscribe"
TYPE_UNSUBSCRIBE  = "unsubscribe"

# Client-Befehle (aus webserver_handler.py)
CMD_BOARD_START     = "board-start"
CMD_BOARD_STOP      = "board-stop"
CMD_BOARD_RESET     = "board-reset"
CMD_BOARD_CALIBRATE = "board-calibrate"
CMD_CORRECT         = "correct"
CMD_NEXT            = "next"
CMD_UNDO            = "undo"
CMD_HELLO           = "hello"

# Allgemeine Daten-Schlüssel (Dictionary Keys)
KEY_EVENT           = "event"
KEY_ID              = "id"
KEY_HITS            = "hits"
KEY_DARTS           = "darts"
KEY_MATCH           = "match"
KEY_MODE            = "mode"
KEY_DATA            = "data"
KEY_DISPLAY_ORDER   = "display_order"
KEY_GAME_MODE       = "gameMode"
KEY_INMODE          = "inMode"
KEY_OUTMODE         = "outMode"
KEY_MAX_ROUNDS      = "maxRounds"
KEY_PLAYERS         = "players"
KEY_SETTINGS        = "settings"
KEY_TURN            = "turn"
KEY_TURNS           = "turns"
KEY_PLAYER          = "player"
KEY_NAME            = "name"
KEY_ORDER           = "order"
KEY_SEGMENT         = "segment"
KEY_ROUND           = "round"
KEY_SCORES          = "scores"
KEY_VARIANT         = "variant"
KEY_STATE           = "state"
KEY_LEG             = "leg"
KEY_LEGS            = "legs"
KEY_SET             = "set"
KEY_SETS            = "sets"
KEY_TYPE            = "type"
KEY_TARGET          = "target"
KEY_TARGETS         = "targets"
KEY_TARGET_SCORE    = "targetScore"
KEY_USER            = "user"
KEY_WINNER          = "winner"
KEY_GAME_WINNER     = "gameWinner"

# Spiel-spezifische Schlüssel
KEY_BASE_SCORE      = "baseScore"
KEY_GAME_SCORES     = "gameScores"
KEY_STATS           = "stats"
KEY_LEG_STATS       = "legStats"
KEY_MATCH_STATS     = "matchStats"
KEY_AVERAGE         = "average"
KEY_OA_AVERAGE      = "overall_average"
KEY_OA_MPR          = "overall_mpr"
KEY_OA_HIT_RATE     = "overall_hit_rate"
KEY_OA_PPR          = "overall_ppr"
KEY_LEGS_TO_WIN     = "legs_to_win"
KEY_SETS_TO_WIN     = "sets_to_win"
KEY_HITRATE         = "hitRate"

# Spezifische Werte
VAL_CARDS           = "cards"
VAL_TABLE           = "table"

# Spiel-Zustände (Game States)
STATE_THROW         = "throw"
STATE_THROWS        = "throws"
STATE_BUSTED        = "busted"
STATE_LEG_WON       = "leg_won"
STATE_MATCH_WON     = "match_won"
STATE_GAME_OVER     = "game_over"
STATE_GAME_FINISHED = "gameFinished"

# Spieler-Typen
PLAYER_TYPE_GUEST      = "guest"
PLAYER_TYPE_REGISTERED = "registered"
PLAYER_TYPE_OWNER      = "owner"

# besondere targets
TARGET_BULL         = "Bull"
TARGET_BULLSEYE     = "Bullseye"
TARGET_SINGLE       = "Single"
TARGET_DOUBLE       = "Double"
TARGET_TRIPLE       = "Triple"