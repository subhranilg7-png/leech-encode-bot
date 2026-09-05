# Handles a video/audio/document sent DIRECTLY to the bot (not a torrent,
# not a magnet link, not via /torrent /magnet /directdl) and routes it
# through the same upload pipeline used by leeches - so /togglecompress
# and /autorename apply to it the same way.

import os
import tempfile
from pyrogram import Client, filters

from .. import ALL_CHATS
from ..utils.db import get_settings
from ..utils.upload_worker import upload_queue

VIDEO_AUDIO_MIME_PREFIXES = ('video/', 'audio/')
VIDEO_AUDIO_EXTENSIONS = (
    '.mkv', '.mp4', '.avi', '.mov', '.webm', '.wmv', '.flv', '.m4v', '.ts', '.3gp',
    '.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.opus',
)


@Client.on_message(filters.chat(ALL_CHATS) & (filters.video | filters.audio | filters.document), group=2)
async def direct_file_send(client, message):
    text = message.text or message.caption
    if text and text.strip().startswith('/'):
        return  # a command is using this message/attachment - let its own handler deal with it

    document = message.document
    if document and document.file_name and document.file_name.lower().endswith('.torrent'):
        return  # handled by autodetect.py instead

    media = message.video or message.audio or document
    if media is None:
        return
    mime_type = getattr(media, 'mime_type', None) or ''
    file_name = (getattr(media, 'file_name', None) or '').lower()
    is_video_or_audio = (
        bool(message.video or message.audio)
        or mime_type.startswith(VIDEO_AUDIO_MIME_PREFIXES)
        or file_name.endswith(VIDEO_AUDIO_EXTENSIONS)
    )
    if not is_video_or_audio:
        return  # e.g. a plain document/image that isn't a video/audio - leave it alone

    user_id = message.from_user.id
    settings = await get_settings(user_id)
    if not settings['compress_enabled']:
        return  # compression is off - nothing for the bot to do with a direct-sent file

    os.makedirs(str(user_id), exist_ok=True)
    tempdir = tempfile.mkdtemp(dir=str(user_id))
    filename = getattr(media, 'file_name', None) or f'{media.file_unique_id}.mp4'
    filepath = os.path.join(tempdir, filename)
    reply = await message.reply_text('Downloading your file to compress it...')
    await message.download(filepath)
    torrent_info = {'dir': tempdir, 'files': [{'path': filepath}]}
    upload_queue.put_nowait((client, message, reply, torrent_info, user_id, ()))
