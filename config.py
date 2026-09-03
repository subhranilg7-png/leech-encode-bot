import os

# --- Telegram ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# --- aria2c RPC (for torrent leeching) ---
ARIA2_RPC_URL = os.environ.get("ARIA2_RPC_URL", "http://localhost:6800/rpc")
ARIA2_RPC_SECRET = os.environ.get("ARIA2_RPC_SECRET", "")

# --- Paths ---
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/home/claude/leech-encode-bot/downloads")
ENCODE_DIR = os.environ.get("ENCODE_DIR", "/home/claude/leech-encode-bot/encoded")
THUMB_DIR = os.environ.get("THUMB_DIR", "/home/claude/leech-encode-bot/thumbnails")
# --- MongoDB (metadata: rename mode, thumbnail path, quality preset, RSS feeds) ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "leech_encode_bot")

# --- Nyaa.si ---
NYAA_BASE_URL = "https://nyaa.si"

# --- Default FFmpeg encode settings (overridable per user) ---
DEFAULT_RESOLUTION = os.environ.get("DEFAULT_RESOLUTION", "1080p")  # 720p / 1080p
DEFAULT_CODEC = os.environ.get("DEFAULT_CODEC", "libx265")
DEFAULT_CRF = os.environ.get("DEFAULT_CRF", "26")
DEFAULT_PRESET = os.environ.get("DEFAULT_PRESET", "medium")

# --- RSS ---
RSS_CHECK_INTERVAL_SECONDS = int(os.environ.get("RSS_CHECK_INTERVAL_SECONDS", "600"))  # 10 min

for path in (DOWNLOAD_DIR, ENCODE_DIR, THUMB_DIR):
    os.makedirs(path, exist_ok=True)
