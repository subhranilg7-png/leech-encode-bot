import os

import config
import db
from modules import encode as encode_mod
from modules import leech as leech_mod
from modules import rename as rename_mod
from modules import thumbnail as thumb_mod


async def run_pipeline(app, chat_id: int, user_id: int, magnet_or_url: str, status_msg=None):
    """
    Full flow used by both manual /leech and the RSS auto-watcher:
    leech -> encode/compress -> rename (per user's mode) -> attach thumbnail -> send.
    """
    async def progress(pct, speed):
        if status_msg:
            try:
                await status_msg.edit_text(f"Leeching... {pct:.1f}% ({speed})")
            except Exception:
                pass

    if status_msg:
        await status_msg.edit_text("Starting leech...")
    downloaded_path = await leech_mod.leech_magnet(magnet_or_url, progress_callback=progress)

    return await encode_and_deliver(app, chat_id, user_id, downloaded_path, status_msg)


async def run_direct_compress(app, chat_id: int, user_id: int, local_file_path: str, status_msg=None):
    """
    Flow for a file the user sent directly to the bot (no leech step):
    encode/compress at the user's chosen quality -> rename -> thumbnail -> send.
    """
    return await encode_and_deliver(app, chat_id, user_id, local_file_path, status_msg)


async def encode_and_deliver(app, chat_id: int, user_id: int, source_path: str, status_msg=None):
    """
    Shared stage for both flows above: encode at the user's selected quality
    preset (480p/720p/1080p — only that one quality is produced), then
    rename and deliver.
    """
    settings = db.get_user_settings(user_id)

    if status_msg:
        await status_msg.edit_text(f"Compressing to {settings['resolution'] or config.DEFAULT_RESOLUTION}...")
    encoded_path = await encode_mod.encode_video(
        source_path,
        resolution=settings["resolution"],
        codec=settings["codec"],
        crf=settings["crf"],
    )

    # ---- rename ----
    if settings["rename_mode"] == "auto":
        try:
            final_path = rename_mod.auto_rename(encoded_path)
        except ValueError:
            # auto-detection failed -> hold for manual rename instead of guessing
            db.set_pending_rename(user_id, encoded_path)
            if status_msg:
                await status_msg.edit_text(
                    "Couldn't auto-detect episode info. Send the full filename you want to use."
                )
            return None
    else:
        # manual mode: hold the file and wait for the user's next message
        db.set_pending_rename(user_id, encoded_path)
        if status_msg:
            await status_msg.edit_text("Encoding done. Send the full filename you want to use.")
        return None

    return await _deliver(app, chat_id, user_id, final_path, status_msg)


async def finish_manual_rename(app, chat_id: int, user_id: int, new_full_name: str, status_msg=None):
    """Called when a user replies with their desired filename after manual rename is pending."""
    pending_path = db.pop_pending_rename(user_id)
    if not pending_path or not os.path.exists(pending_path):
        if status_msg:
            await status_msg.edit_text("No file waiting to be renamed.")
        return None

    final_path = rename_mod.manual_rename(pending_path, new_full_name)
    return await _deliver(app, chat_id, user_id, final_path, status_msg)


async def _deliver(app, chat_id: int, user_id: int, file_path: str, status_msg=None):
    thumb_path = thumb_mod.get_user_thumbnail_path(user_id)

    if status_msg:
        await status_msg.edit_text("Uploading...")

    sent = await app.send_document(
        chat_id=chat_id,
        document=file_path,
        thumb=thumb_path,
        caption=os.path.basename(file_path),
    )

    if status_msg:
        await status_msg.delete()

    return sent
