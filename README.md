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

1. Open this repo in a Codespace (Code → Codespaces → New codespace). The
   `.devcontainer/devcontainer.json` automatically installs `ffmpeg`,
   `aria2c`, and the Python dependencies when the Codespace is created.
2. Add your secrets under repo → Settings → Secrets and variables →
   Codespaces, then add each of:
   - `BOT_TOKEN`, `API_ID`, `API_HASH` — from @BotFather and https://my.telegram.org
   - `OWNER_ID` — your Telegram user ID
   - `ARIA2_RPC_SECRET` — any random string
   They'll be available as environment variables automatically next time
   you open (or rebuild) the Codespace — no `.env` file needed.
3. Run it:
   ```bash
   python bot.py
   ```
   `bot.py` starts aria2c's RPC daemon itself in the background if it isn't
   already running, so this one command is all you need. If you ever change
   `.devcontainer/devcontainer.json`, use "Rebuild Container" from the
   Codespaces menu so the setup step reruns.
4. Message your bot `/start` on Telegram to confirm it's alive.

`.env.sample` is kept purely as a reference for which variables to add as
Codespaces secrets — you don't need to create an actual `.env` file.

## Alternative: Docker

If you'd rather run it in a container instead of directly in the Codespace:

```bash
docker build -t leech-encode-bot .
docker run \
  -e BOT_TOKEN \
  -e API_ID \
  -e API_HASH \
  -e OWNER_ID \
  -e ARIA2_RPC_SECRET \
  leech-encode-bot
```

Or with `docker-compose.yml` (persists downloads/thumbnails/settings across
rebuilds): `docker compose up -d`.

## Local (non-Codespaces) run

Requires `ffmpeg` and `aria2c` installed on the system, and the same five
env vars exported into your shell.

```bash
pip install -r requirements.txt
python bot.py
```

## Notes

- The RSS watcher polls every `RSS_CHECK_INTERVAL_SECONDS` (default 10 min)
  and only fires for entries newer than the last one it saw per feed, so
  restarts won't re-leech old episodes.
- Multi-file torrents: the leech step picks the largest file (the episode
  video), skipping .nfo/sample files.
- All per-user state (rename mode, thumbnail, encode prefs, RSS feeds) lives
  in `bot.db` (SQLite) — back this file up if you redeploy.
