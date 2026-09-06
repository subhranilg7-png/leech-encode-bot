# lazyleech - settings storage (MongoDB)
#
# Stores per-user preferences: auto-rename format, rename mode, and
# direct-file compression toggle/quality. Replaces the old SQLite
# approach used in earlier bots in this series.

import motor.motor_asyncio
from .. import MONGO_URI

_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
_db = _client['lazyleech'] if _client else None
_settings = _db['user_settings'] if _db is not None else None

DEFAULTS = {
    'auto_rename_enabled': False,
    'rename_format': None,       # template string, e.g. "{title} S{season}E{episode} [{quality}]"
    'compress_enabled': False,   # direct-file compression toggle, off by default

    # Granular encode settings (used by utils/compress.py). Replaces the old
    # fixed 480p/720p/1080p-only preset system with independent controls,
    # same axes as the reference encode bots: codec, CRF, preset, 10-bit,
    # resolution, and audio handling.
    'encode_format': 'mkv',       # container: mkv, mp4, avi
    'encode_codec': 'h264',       # h264 or h265
    'encode_crf': 26,             # lower = higher quality/bigger file, roughly 18-32
    'encode_preset': 'fast',      # ultrafast..veryslow (ffmpeg x264/x265 presets)
    'encode_10bit': False,        # 10-bit encoding (h265 only - ignored for h264)
    'encode_resolution': 'original',  # original, 1080p, 720p, 540p, 480p, 360p
    'encode_audio_codec': 'aac',  # copy, aac, ac3, opus, mp3
    'encode_audio_bitrate': '128k',
    'encode_audio_channels': 'original',  # original, mono, stereo, 5.1

    # Video-container metadata (e.g. the "title" tag players show) - reuses
    # the same {title}/{season}/{episode}/{quality} template placeholders
    # as auto-rename, applied to the encoded file's metadata, not just its
    # filename.
    'metadata_enabled': False,
    'metadata_template': '{title} S{season}E{episode}',
}

async def get_settings(user_id):
    if _settings is None:
        return dict(DEFAULTS)
    doc = await _settings.find_one({'_id': user_id})
    if not doc:
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in doc.items() if k != '_id'})
    return merged

async def set_setting(user_id, key, value):
    if _settings is None:
        raise RuntimeError('MONGO_URI is not configured')
    await _settings.update_one({'_id': user_id}, {'$set': {key: value}}, upsert=True)

async def get_setting(user_id, key):
    settings = await get_settings(user_id)
    return settings.get(key, DEFAULTS.get(key))
