import hashlib
import string
import time

BOS_TOKEN = "[BOS]"
EOS_TOKEN = "[EOS]"
PAD_TOKEN = "[PAD]"
UNK_TOKEN = "[UNK]"

CUSTOM_HANDLER_SENTINEL = object()

IMS = 0

HASH_ALGORITHMS = {
    "MD5": hashlib.md5,
    "MD4": hashlib.new, 
    "SHA-1": hashlib.sha1,
    "SHA-224": hashlib.sha224,
    "SHA-256": hashlib.sha256,
    "SHA-384": hashlib.sha384,
    "BLAKE2b": hashlib.blake2b,
    "BLAKE2s": hashlib.blake2s,
    "SHA-512": hashlib.sha512,
    "SHA3-256": hashlib.sha3_256,
    "SHA3-384": hashlib.sha3_384,
    "SHA3-512": hashlib.sha3_512,
    "RIPEMD160": hashlib.new, 
    "SHAKE128-256": hashlib.shake_128,
    "SHAKE256-512": hashlib.shake_256,

    "Whirlpool": hashlib.new, 
    "CRC32 (HEX)": CUSTOM_HANDLER_SENTINEL,
    "Murmur3_32": CUSTOM_HANDLER_SENTINEL,
    "Murmur3_128": CUSTOM_HANDLER_SENTINEL,
    "CityHash64": CUSTOM_HANDLER_SENTINEL,
    "CityHash128": CUSTOM_HANDLER_SENTINEL,
    "XXH32": CUSTOM_HANDLER_SENTINEL,
    "XXH64": CUSTOM_HANDLER_SENTINEL,
    "XXH3_64": CUSTOM_HANDLER_SENTINEL,
    "XXH3_128": CUSTOM_HANDLER_SENTINEL,
    "AES-EMU-SHA256": CUSTOM_HANDLER_SENTINEL, 
}
ALL_HASH_TYPES = ["Auto-Detect", "bcrypt"] + list(HASH_ALGORITHMS.keys())
DEFAULT_CHARSET = string.ascii_letters + string.digits + string.punctuation

MAX_BRUTEFORCE_COMBINATIONS_FOR_PROGRESS = 10**9
PROBABILISTIC_CANDIDATES_PER_STRUCTURE_CHUNK = 50
PROBABILISTIC_GEN_BATCH_SIZE = 10
DEFAULT_PROBABILISTIC_CANDIDATES = 100000
DEFAULT_PROBABILISTIC_MAX_LEN = 32
PROBABILISTIC_TOP_K = 50
PROBABILISTIC_TOP_P = 0.95
PROBABILISTIC_TEMPERATURE = 0.8

BG_COLOR = "#0a0a0a"
FG_COLOR = "#00ff41"
ACCENT_COLOR = "#00d4ff"
SECONDARY_ACCENT = "#ff6b00"
EXPORT_COLOR = "#7A918D"
ERROR_COLOR = "#ff0040"
SUCCESS_COLOR = "#00ff88"
OPTIMIZE_COLOR = "#7EBDC3"
WARNING_COLOR = "#ffaa00"

DISABLED_FG_COLOR = "#666666"
TITLES_COLOR = "#fbfcfc"
BUTTON_BG_COLOR = "#1a1a1a"
BUTTON_ACTIVE_BG_COLOR = "#2a2a2a"
BUTTON_HOVER_COLOR = "#333333"
ENTRY_BG_COLOR = "#0f0f0f"
PROGRESS_TROUGH_COLOR = "#1a1a1a"
PROGRESS_BAR_COLOR = FG_COLOR
TEXTBOX_BG_COLOR = "#080808"
SCROLLBAR_BUTTON_COLOR = BUTTON_BG_COLOR
SCROLLBAR_BUTTON_HOVER_COLOR = BUTTON_ACTIVE_BG_COLOR
DARK_RED_HOVER_COLOR = "#cc0033"

BORDER_COLOR = "#333333"
HIGHLIGHT_COLOR = "#00ff41"
GLOW_COLOR = "#00ff4155"

PULSE_COLOR_1 = "#00ff41"
PULSE_COLOR_2 = "#00aa2a"

FONT_FAMILY_MONO = ("Fira Code", 10, "normal")
FONT_FAMILY_UI = ("Fira Code", 11, "normal")
FONT_FAMILY_TITLE = ("Quantico", 14, "bold")
FONT_FAMILY_HEADER = ("Fira Code", 12, "bold")
FONT_FAMILY_LOG = ("Fira Code", 11, "normal")
FONT_FAMILY_BUTTON = ("Fira Code", 10, "bold")

LEET_MAP_SIMPLE = {
    'a': '@', 'e': '3', 's': '$', 'o': '0', 'i': '1', 'l': '1', 't': '7', 'g': '9', 'b': '8',
    'A': '@', 'E': '3', 'S': '$', 'O': '0', 'I': '1', 'L': '1', 'T': '7', 'G': '9', 'B': '8'
}
COMMON_YEARS = [str(y) for y in range(int(time.strftime("%Y")) - 5, int(time.strftime("%Y")) + 2)]
NUMBERS_TO_APPEND = [str(i) for i in range(10)] + \
                      ["00", "01", "12", "23", "123", "321", "1234", "4321", "12345", "54321"] + \
                      COMMON_YEARS + \
                      ["!", "!!", "@", "#", "$", "%", "^", "&", "*", "?", "_", "-"] + \
                      [f"{y}!" for y in COMMON_YEARS] + [f"!{y}" for y in COMMON_YEARS]

COMMON_PREFIXES = ["", "admin", "pass", "user", "test"]
COMMON_SUFFIXES = ["", "1", "123", "!", "!!", "2023", "2024", "2025", "pass", "admin"]

RAINBOW_TABLE_DB_PATH = "rainbow_tables.db"
RAINBOW_TABLE_CACHE_SIZE = 50000  
RAINBOW_TABLE_BATCH_SIZE = 1000   
RAINBOW_TABLE_BLOOM_FILTER_SIZE = 10000000  
RAINBOW_TABLE_BLOOM_HASH_COUNT = 7  
RAINBOW_TABLE_COMPRESSION_LEVEL = 6  
RAINBOW_TABLE_MAX_PASSWORD_LENGTH = 64
RAINBOW_TABLE_INDEX_REBUILD_THRESHOLD = 100000  

RAINBOW_TABLE_CHUNK_SIZE = 10000  
RAINBOW_TABLE_MEMORY_LIMIT_MB = 512  
RAINBOW_TABLE_PARALLEL_WORKERS = 4  
RAINBOW_TABLE_PRELOAD_POPULAR_HASHES = True

BASE_RAINBOW_TABLES = [
    "rockyou_hashes.db",
    "common_passwords_hashes.db",
    "leaked_hashes.db"
]