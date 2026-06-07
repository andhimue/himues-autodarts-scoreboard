# Backend/modules/core/constants.py

# Event-Namen
EVT_GAME_UPDATE   = "game-update"
EVT_MATCH_ENDED   = "match-ended"
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

FIELD_COORDS = {
    "0":   {"x": 0.016160134143785285,  "y": 1.1049884720184449},       "S1":  {"x": 0.2415216935652902,    "y": 0.7347516243974009},
    "D1":  {"x": 0.29786208342066656,   "y": 0.9359673024523162},       "T1":  {"x": 0.17713267658771747,   "y": 0.5818277090756655},
    "S2":  {"x": 0.4668832529867955,    "y": -0.6415636134982183},      "D2":  {"x": 0.5876126598197445,    "y": -0.7783902745755609},
    "T2":  {"x": 0.35420247327604254,   "y": -0.4725424439320897},      "S3":  {"x": 0.008111507021588693,  "y": -0.7864389016977573},
    "D3":  {"x": -0.007985747222804492, "y": -0.9715573255082791},      "T3":  {"x": -0.007985747222804492, "y": -0.5932718507650387},
    "S4":  {"x": 0.6439530496751206,    "y": 0.4530496751205198},       "D4":  {"x": 0.7888283378746596,    "y": 0.5657304548312723},
    "T4":  {"x": 0.48298050723118835,   "y": 0.36451477677635713},      "S5":  {"x": -0.23334730664430925,  "y": 0.7508488786417943},
    "D5":  {"x": -0.31383357786627536,  "y": 0.9279186753301195},       "T5":  {"x": -0.1850555439111297,   "y": 0.5737790819534688},
    "S6":  {"x": 0.7888283378746596,    "y": -0.013770697966883233},    "D6":  {"x": 0.9739467616851814,    "y": 0.010375183399706544},
    "T6":  {"x": 0.5956612869419406,    "y": -0.005722070844686641},    "S7":  {"x": -0.4506602389436176,   "y": -0.6335149863760215},
    "D7":  {"x": -0.5713896457765667,   "y": -0.7703416474533641},      "T7":  {"x": -0.3540767134772585,   "y": -0.4725424439320897},
    "S8":  {"x": -0.7323621882204988,   "y": -0.239132257388388},       "D8":  {"x": -0.9255292391532174,   "y": -0.2954726472437643},
    "T8":  {"x": -0.5713896457765667,   "y": -0.18279186753301202},     "S9":  {"x": -0.627730035631943,    "y": 0.4691469293649132},
    "D9":  {"x": -0.7726053238314818,   "y": 0.5657304548312723},       "T9":  {"x": -0.48285474743240414,  "y": 0.34841752253196395},
    "S10": {"x": 0.7244393208970865,    "y": -0.23108363026619158},     "D10": {"x": 0.9256549989520018,    "y": -0.28742402012156787},
    "T10": {"x": 0.5715154055753511,    "y": -0.19084049465520878},     "S11": {"x": -0.7726053238314818,   "y": -0.005722070844686641},
    "D11": {"x": -0.9657723747642004,   "y": -0.005722070844686641},    "T11": {"x": -0.5955355271431566,   "y": 0.0023265562775099512},
    "S12": {"x": -0.4506602389436176,   "y": 0.6140222175644519},       "D12": {"x": -0.5633410186543703,   "y": 0.7910920142527772},
    "T12": {"x": -0.3540767134772585,   "y": 0.4932928107315028},       "S13": {"x": 0.7244393208970865,    "y": 0.24378536994340808},
    "D13": {"x": 0.917606371829805,     "y": 0.308174386920981},        "T13": {"x": 0.5634667784531546,    "y": 0.18744498008803193},
    "S14": {"x": -0.7223277562650692,   "y": 0.2440637100898663},       "D14": {"x": -0.9255292391532174,   "y": 0.308174386920981},
    "T14": {"x": -0.5713896457765667,   "y": 0.19549360721022835},      "S15": {"x": 0.6278557954307273,    "y": -0.46449381680989327},
    "D15": {"x": 0.7888283378746596,    "y": -0.5771745965206456},      "T15": {"x": 0.4910291343533851,    "y": -0.34376440997694424},
    "S16": {"x": -0.6196814085097464,   "y": -0.4725424439320897},      "D16": {"x": -0.7967512051980717,   "y": -0.5610773422762524},
    "T16": {"x": -0.49090337455460076,  "y": -0.33571578285474746},     "S17": {"x": 0.2415216935652902,    "y": -0.730098511842381},
    "D17": {"x": 0.29786208342066656,   "y": -0.9152169356529029},      "T17": {"x": 0.18518130370991423,   "y": -0.5691259693984492},
    "S18": {"x": 0.48298050723118835,   "y": 0.6462167260532384},       "D18": {"x": 0.5554181513309578,    "y": 0.799140641374974},
    "T18": {"x": 0.3292712798530314,    "y": 0.49608083282302506},      "S19": {"x": -0.2586037966932027,   "y": -0.7658909981628906},
    "D19": {"x": -0.3134721371708513,   "y": -0.9148193508879362},      "T19": {"x": -0.19589712186160443,  "y": -0.562094304960196},
    "S20": {"x": 0.00006123698714003468,"y": 0.7939375382731171},       "D20": {"x": 0.01119619445411297,   "y": 0.9726766446223462},
    "T20": {"x": 0.00006123698714003468,"y": 0.6058175137783223},       "25":  {"x": 0.06276791181873864,   "y": 0.01794243723208814},
    "50": {"x": -0.007777097366809472,  "y": 0.0022657685241886157},
}

