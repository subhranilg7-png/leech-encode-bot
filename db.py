from pymongo import MongoClient, ReturnDocument

import config

_client = MongoClient(config.MONGO_URI)
_db = _client[config.MONGO_DB_NAME]

user_settings_col = _db["user_settings"]
rss_feeds_col = _db["rss_feeds"]
pending_rename_col = _db["pending_rename"]
counters_col = _db["counters"]

_DEFAULT_SETTINGS = {
    "rename_mode": "manual",          # 'manual' or 'auto'
    "thumbnail_path": None,
    "resolution": None,               # quality preset: 480p / 720p / 1080p
    "codec": None,
    "crf": None,
    "direct_compress_mode": "off",    # 'on' or 'off': compress files sent directly
}


def init_db():
    """Creates indexes. Collections/documents are created on first write."""
    rss_feeds_col.create_index("user_id")
    rss_feeds_col.create_index("id", unique=True)


def _next_feed_id() -> int:
    doc = counters_col.find_one_and_update(
        {"_id": "rss_feed_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


# ---------- user settings ----------

def get_user_settings(user_id: int) -> dict:
    doc = user_settings_col.find_one({"_id": user_id})
    if doc is None:
        doc = {"_id": user_id, **_DEFAULT_SETTINGS}
        user_settings_col.insert_one(doc)
    else:
        # fill in any fields added after this user's doc was first created
        missing = {k: v for k, v in _DEFAULT_SETTINGS.items() if k not in doc}
        if missing:
            user_settings_col.update_one({"_id": user_id}, {"$set": missing})
            doc.update(missing)
    return doc


def set_rename_mode(user_id: int, mode: str):
    assert mode in ("manual", "auto")
    get_user_settings(user_id)  # ensure doc exists
    user_settings_col.update_one({"_id": user_id}, {"$set": {"rename_mode": mode}})


def set_thumbnail(user_id: int, path: str):
    get_user_settings(user_id)
    user_settings_col.update_one({"_id": user_id}, {"$set": {"thumbnail_path": path}})


def clear_thumbnail(user_id: int):
    user_settings_col.update_one({"_id": user_id}, {"$set": {"thumbnail_path": None}})


def set_encode_prefs(user_id: int, resolution=None, codec=None, crf=None):
    get_user_settings(user_id)
    updates = {}
    if resolution:
        updates["resolution"] = resolution
    if codec:
        updates["codec"] = codec
    if crf:
        updates["crf"] = crf
    if updates:
        user_settings_col.update_one({"_id": user_id}, {"$set": updates})


def set_quality_preset(user_id: int, quality: str):
    """Quality preset the user's files are compressed to: 480p / 720p / 1080p."""
    assert quality in ("480p", "720p", "1080p")
    get_user_settings(user_id)
    user_settings_col.update_one({"_id": user_id}, {"$set": {"resolution": quality}})


def set_direct_compress_mode(user_id: int, mode: str):
    assert mode in ("on", "off")
    get_user_settings(user_id)
    user_settings_col.update_one({"_id": user_id}, {"$set": {"direct_compress_mode": mode}})


# ---------- pending manual rename ----------

def set_pending_rename(user_id: int, file_path: str):
    pending_rename_col.update_one(
        {"_id": user_id},
        {"$set": {"file_path": file_path}},
        upsert=True,
    )


def pop_pending_rename(user_id: int):
    doc = pending_rename_col.find_one_and_delete({"_id": user_id})
    return doc["file_path"] if doc else None


# ---------- RSS feeds ----------

def add_rss_feed(user_id: int, feed_url: str, include: str = "", exclude: str = ""):
    rss_feeds_col.insert_one({
        "id": _next_feed_id(),
        "user_id": user_id,
        "feed_url": feed_url,
        "filter_include": include,
        "filter_exclude": exclude,
        "last_seen_link": "",
    })


def list_rss_feeds(user_id: int = None):
    query = {} if user_id is None else {"user_id": user_id}
    return list(rss_feeds_col.find(query))


def update_last_seen(feed_id: int, link: str):
    rss_feeds_col.update_one({"id": feed_id}, {"$set": {"last_seen_link": link}})


def remove_rss_feed(feed_id: int, user_id: int):
    rss_feeds_col.delete_one({"id": feed_id, "user_id": user_id})
