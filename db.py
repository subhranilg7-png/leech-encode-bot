import sqlite3
import threading
from contextlib import contextmanager

import config

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                rename_mode TEXT DEFAULT 'manual',      -- 'manual' or 'auto'
                thumbnail_path TEXT DEFAULT NULL,
                resolution TEXT DEFAULT NULL,           -- quality preset: 480p / 720p / 1080p
                codec TEXT DEFAULT NULL,
                crf TEXT DEFAULT NULL,
                direct_compress_mode TEXT DEFAULT 'off'  -- 'on' or 'off': compress files sent directly
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feed_url TEXT NOT NULL,
                filter_include TEXT DEFAULT '',
                filter_exclude TEXT DEFAULT '',
                last_seen_link TEXT DEFAULT ''
            )
        """)
        try:
            conn.execute("ALTER TABLE user_settings ADD COLUMN direct_compress_mode TEXT DEFAULT 'off'")
        except sqlite3.OperationalError:
            pass  # column already exists

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_rename (
                user_id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL
            )
        """)


# ---------- user settings ----------

def get_user_settings(user_id: int) -> sqlite3.Row:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
            row = conn.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
        return row


def set_rename_mode(user_id: int, mode: str):
    assert mode in ("manual", "auto")
    get_user_settings(user_id)  # ensure row exists
    with get_conn() as conn:
        conn.execute("UPDATE user_settings SET rename_mode=? WHERE user_id=?", (mode, user_id))


def set_thumbnail(user_id: int, path: str):
    get_user_settings(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE user_settings SET thumbnail_path=? WHERE user_id=?", (path, user_id))


def clear_thumbnail(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE user_settings SET thumbnail_path=NULL WHERE user_id=?", (user_id,))


def set_encode_prefs(user_id: int, resolution=None, codec=None, crf=None):
    get_user_settings(user_id)
    with get_conn() as conn:
        if resolution:
            conn.execute("UPDATE user_settings SET resolution=? WHERE user_id=?", (resolution, user_id))
        if codec:
            conn.execute("UPDATE user_settings SET codec=? WHERE user_id=?", (codec, user_id))
        if crf:
            conn.execute("UPDATE user_settings SET crf=? WHERE user_id=?", (crf, user_id))


def set_quality_preset(user_id: int, quality: str):
    """Quality preset the user's files are compressed to: 480p / 720p / 1080p."""
    assert quality in ("480p", "720p", "1080p")
    get_user_settings(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE user_settings SET resolution=? WHERE user_id=?", (quality, user_id))


def set_direct_compress_mode(user_id: int, mode: str):
    assert mode in ("on", "off")
    get_user_settings(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE user_settings SET direct_compress_mode=? WHERE user_id=?", (mode, user_id))


# ---------- pending manual rename ----------

def set_pending_rename(user_id: int, file_path: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pending_rename (user_id, file_path) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET file_path=excluded.file_path",
            (user_id, file_path),
        )


def pop_pending_rename(user_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT file_path FROM pending_rename WHERE user_id=?", (user_id,)).fetchone()
        if row:
            conn.execute("DELETE FROM pending_rename WHERE user_id=?", (user_id,))
            return row["file_path"]
        return None


# ---------- RSS feeds ----------

def add_rss_feed(user_id: int, feed_url: str, include: str = "", exclude: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO rss_feeds (user_id, feed_url, filter_include, filter_exclude) VALUES (?, ?, ?, ?)",
            (user_id, feed_url, include, exclude),
        )


def list_rss_feeds(user_id: int = None):
    with get_conn() as conn:
        if user_id is None:
            return conn.execute("SELECT * FROM rss_feeds").fetchall()
        return conn.execute("SELECT * FROM rss_feeds WHERE user_id=?", (user_id,)).fetchall()


def update_last_seen(feed_id: int, link: str):
    with get_conn() as conn:
        conn.execute("UPDATE rss_feeds SET last_seen_link=? WHERE id=?", (link, feed_id))


def remove_rss_feed(feed_id: int, user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM rss_feeds WHERE id=? AND user_id=?", (feed_id, user_id))
