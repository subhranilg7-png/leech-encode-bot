# Leech + Encode + Compress Bot

Telegram bot that leeches torrents (primarily from nyaa.si), encodes/compresses
them with FFmpeg, renames them, attaches a per-user thumbnail, and delivers
the result back on Telegram. Supports both manual leeching and RSS-automated
leeching.

## Features

- **Leech**: `/leech <magnet or link>` — download via aria2c, encode, deliver
- **Search**: `/search <query>` — search nyaa.si, returns magnet links to leech
- **RSS automation**: `/rss add <feed_url>` — auto-leech new matching episodes
  as they're published, no manual searching required
- **Direct file compress**: `/directcompress on|off` — off by default. When
  on, any video/document you send the bot directly (no torrent) gets
  encoded/compressed and sent back through the same rename+thumbnail
  pipeline as a leech.
- **Quality preset**: `/setquality 480p|720p|1080p` — sets the single
  resolution your files get compressed to. Only that one quality is
  produced (not all three) — applies to both `/leech` and direct compress.
- **Rename**:
  - Manual mode: after encoding, send one message with the full filename you
    want — no separate episode/season/quality prompts
  - Auto mode: detects season/episode/quality from the source filename via
    regex and renames automatically; falls back to manual if detection fails
- **Thumbnail**: reply to a photo with `/setthumb` — it's center-cropped to a
  square (pixel-based crop from the image's center, no stretching) and
  applied to every file you leech until you `/clearthumb`
- **Per-user encode settings**: `/setencode <resolution> <codec> <crf>`

## Setup (GitHub Codespaces)

1. Open this repo in a Codespace (Code → Codespaces → New codespace).
2. Copy `.env.sample` to `.env` and fill in:
   - `BOT_TOKEN`, `API_ID`, `API_HASH` — from @BotFather and https://my.telegram.org
   - `OWNER_ID` — your Telegram user ID
   - `ARIA2_RPC_SECRET` — any random string
3. Build and run:
   ```bash
   docker build -t leech-encode-bot .
   docker run --env-file .env leech-encode-bot
   ```
4. Message your bot `/start` on Telegram to confirm it's alive.

## Local (non-Docker) run

Requires `ffmpeg` and `aria2c` installed on the system.

```bash
pip install -r requirements.txt
aria2c --enable-rpc --rpc-listen-all=false --rpc-secret=<same as .env> -D --dir=./downloads
export $(cat .env | xargs)
python main.py
```

## Notes

- The RSS watcher polls every `RSS_CHECK_INTERVAL_SECONDS` (default 10 min)
  and only fires for entries newer than the last one it saw per feed, so
  restarts won't re-leech old episodes.
- Multi-file torrents: the leech step picks the largest file (the episode
  video), skipping .nfo/sample files.
- All per-user state (rename mode, thumbnail, encode prefs, RSS feeds) lives
  in `bot.db` (SQLite) — back this file up if you redeploy.
