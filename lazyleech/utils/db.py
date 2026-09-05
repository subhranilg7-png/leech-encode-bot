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
    'compress_quality': '720p',  # one of: 480p, 720p, 1080p
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
