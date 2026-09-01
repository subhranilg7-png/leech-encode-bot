import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

import config
import db
from modules import nyaa_search
from modules import pipeline
from modules import rss as rss_mod
from modules import thumbnail as thumb_mod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = Client(
    "leech_encode_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)


# ---------------- basic commands ----------------

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text(
        "Leech + Encode + Compress bot.\n\n"
        "/leech <magnet or nyaa link> - download, encode, deliver\n"
        "/search <query> - search nyaa.si\n"
        "/directcompress on|off - compress files you send directly (no torrent)\n"
        "/setquality 480p|720p|1080p - choose the single quality files are compressed to\n"
        "/settings - view/change rename, thumbnail, encode settings\n"
        "/rss add <feed_url> [include=..] [exclude=..] - auto-leech new matches\n"
        "/rss list - show your feeds\n"
        "/rss remove <id> - stop a feed"
    )


@app.on_message(filters.command("leech"))
async def leech_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /leech <magnet or link>")
        return

    magnet_or_url = message.text.split(None, 1)[1].strip()
    status = await message.reply_text("Queued...")
    try:
        await pipeline.run_pipeline(app, message.chat.id, message.from_user.id, magnet_or_url, status)
    except Exception as e:
        logger.exception("Leech pipeline failed")
        await status.edit_text(f"Failed: {e}")


@app.on_message(filters.command("search"))
async def search_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /search <query>")
        return

    query = message.text.split(None, 1)[1].strip()
    results = nyaa_search.search_nyaa(query)
    if not results:
        await message.reply_text("No results found on nyaa.si.")
        return

    # Store results on the message context so a follow-up number picks one.
    # Simple approach: include the magnet inline as a numbered list, user
    # replies with /leech <magnet> from the list, or we could add inline buttons.
    text = "Results:\n\n" + nyaa_search.format_results(results)
    text += "\n\nUse /leech <magnet> with a result's magnet link to download it."
    await message.reply_text(text[:4000])


# ---------------- settings ----------------

@app.on_message(filters.command("settings"))
async def settings_cmd(client: Client, message: Message):
    s = db.get_user_settings(message.from_user.id)
    thumb = "set" if thumb_mod.get_user_thumbnail_path(message.from_user.id) else "not set"
    await message.reply_text(
        f"Rename mode: {s['rename_mode']}\n"
        f"Thumbnail: {thumb}\n"
        f"Quality preset: {s['resolution'] or config.DEFAULT_RESOLUTION}\n"
        f"Codec: {s['codec'] or config.DEFAULT_CODEC}\n"
        f"CRF: {s['crf'] or config.DEFAULT_CRF}\n"
        f"Direct-file compress: {s['direct_compress_mode']}\n\n"
        "/setrename auto|manual\n"
        "/setthumb (reply to a photo)\n"
        "/clearthumb\n"
        "/setquality 480p|720p|1080p\n"
        "/setencode <resolution> <codec> <crf>\n"
        "/directcompress on|off"
    )


@app.on_message(filters.command("setrename"))
async def setrename_cmd(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1] not in ("auto", "manual"):
        await message.reply_text("Usage: /setrename auto|manual")
        return
    db.set_rename_mode(message.from_user.id, message.command[1])
    await message.reply_text(f"Rename mode set to {message.command[1]}.")


@app.on_message(filters.command("setthumb"))
async def setthumb_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.photo:
        await message.reply_text("Reply to a photo with /setthumb.")
        return

    tmp_path = await target.download(file_name=f"{config.THUMB_DIR}/tmp_{message.from_user.id}.jpg")
    thumb_mod.save_user_thumbnail(message.from_user.id, tmp_path)
    await message.reply_text("Thumbnail saved (center-cropped to square).")


@app.on_message(filters.command("clearthumb"))
async def clearthumb_cmd(client: Client, message: Message):
    thumb_mod.clear_user_thumbnail(message.from_user.id)
    await message.reply_text("Thumbnail cleared.")


@app.on_message(filters.command("setencode"))
async def setencode_cmd(client: Client, message: Message):
    parts = message.command[1:]
    if len(parts) != 3:
        await message.reply_text("Usage: /setencode <resolution> <codec> <crf>  e.g. /setencode 720p libx265 26")
        return
    resolution, codec, crf = parts
    db.set_encode_prefs(message.from_user.id, resolution=resolution, codec=codec, crf=crf)
    await message.reply_text("Encode settings updated.")


@app.on_message(filters.command("setquality"))
async def setquality_cmd(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1] not in ("480p", "720p", "1080p"):
        await message.reply_text("Usage: /setquality 480p|720p|1080p")
        return
    quality = message.command[1]
    db.set_quality_preset(message.from_user.id, quality)
    await message.reply_text(f"Quality preset set to {quality}. Files will be compressed to {quality} only.")


@app.on_message(filters.command("directcompress"))
async def directcompress_cmd(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1] not in ("on", "off"):
        s = db.get_user_settings(message.from_user.id)
        await message.reply_text(
            f"Direct-file compress is currently: {s['direct_compress_mode']}\n"
            "Usage: /directcompress on|off\n\n"
            "When on, any video/document you send the bot directly gets "
            "encoded/compressed at your /setquality preset, renamed, and "
            "sent back — no torrent needed."
        )
        return
    mode = message.command[1]
    db.set_direct_compress_mode(message.from_user.id, mode)
    await message.reply_text(f"Direct-file compress turned {mode}.")


# ---------------- RSS ----------------

@app.on_message(filters.command("rss"))
async def rss_cmd(client: Client, message: Message):
    parts = message.command[1:]
    if not parts:
        await message.reply_text("Usage: /rss add <url> [include=a,b] [exclude=c,d] | /rss list | /rss remove <id>")
        return

    action = parts[0]

    if action == "add" and len(parts) >= 2:
        feed_url = parts[1]
        include = exclude = ""
        for p in parts[2:]:
            if p.startswith("include="):
                include = p[len("include="):]
            elif p.startswith("exclude="):
                exclude = p[len("exclude="):]
        db.add_rss_feed(message.from_user.id, feed_url, include, exclude)
        await message.reply_text("RSS feed added. New matching episodes will be leeched automatically.")

    elif action == "list":
        feeds = db.list_rss_feeds(message.from_user.id)
        if not feeds:
            await message.reply_text("No RSS feeds subscribed.")
            return
        lines = [f"{f['id']}: {f['feed_url']} (include={f['filter_include']!r} exclude={f['filter_exclude']!r})"
                 for f in feeds]
        await message.reply_text("\n".join(lines))

    elif action == "remove" and len(parts) >= 2:
        db.remove_rss_feed(int(parts[1]), message.from_user.id)
        await message.reply_text("Feed removed.")

    else:
        await message.reply_text("Usage: /rss add <url> [include=a,b] [exclude=c,d] | /rss list | /rss remove <id>")


# ---------------- direct file compress (no torrent) ----------------
# Only fires when the sender turned this on via /directcompress on.
# Off by default so a stray file being sent doesn't trigger anything.

@app.on_message(filters.video | filters.document)
async def direct_file_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    settings = db.get_user_settings(user_id)

    if settings["direct_compress_mode"] != "on":
        await message.reply_text(
            "Direct-file compress is off. Turn it on with /directcompress on "
            "if you want me to compress files you send me directly."
        )
        return

    status = await message.reply_text("Downloading your file...")
    try:
        local_path = await message.download(file_name=config.DOWNLOAD_DIR + "/")
        await pipeline.run_direct_compress(app, message.chat.id, user_id, local_path, status)
    except Exception as e:
        logger.exception("Direct file compress failed")
        await status.edit_text(f"Failed: {e}")


# ---------------- manual rename follow-up ----------------
# When manual rename mode holds a file, the user's *next plain text message*
# (not a command) is treated as the full desired filename.

@app.on_message(filters.text & ~filters.command(["start", "leech", "search", "settings",
                                                  "setrename", "setthumb", "clearthumb",
                                                  "setencode", "rss"]))
async def maybe_rename_reply(client: Client, message: Message):
    pending = db.pop_pending_rename(message.from_user.id)
    if pending is None:
        return  # not awaiting a rename; ignore

    # put it back since finish_manual_rename pops it again internally
    db.set_pending_rename(message.from_user.id, pending)

    status = await message.reply_text("Renaming...")
    try:
        await pipeline.finish_manual_rename(app, message.chat.id, message.from_user.id, message.text, status)
    except Exception as e:
        logger.exception("Manual rename/delivery failed")
        await status.edit_text(f"Failed: {e}")


# ---------------- RSS auto-leech background loop ----------------

async def on_new_rss_entry(user_id: int, entry):
    magnet = entry.get("nyaa_magneturi") or entry.get("link", "")
    try:
        await pipeline.run_pipeline(app, user_id, user_id, magnet, status_msg=None)
    except Exception:
        logger.exception(f"RSS auto-leech failed for user {user_id}, entry {entry.get('title')}")


async def start_background_tasks():
    asyncio.create_task(rss_mod.rss_loop(on_new_rss_entry))


if __name__ == "__main__":
    db.init_db()

    async def runner():
        await app.start()
        await start_background_tasks()
        logger.info("Bot started.")
        await asyncio.Event().wait()  # run forever

    asyncio.run(runner())
