import asyncio
import logging

import feedparser

import config
import db

logger = logging.getLogger("rss")


def _entry_matches(title: str, include: str, exclude: str) -> bool:
    title_lower = title.lower()
    if include:
        include_terms = [t.strip().lower() for t in include.split(",") if t.strip()]
        if not any(term in title_lower for term in include_terms):
            return False
    if exclude:
        exclude_terms = [t.strip().lower() for t in exclude.split(",") if t.strip()]
        if any(term in title_lower for term in exclude_terms):
            return False
    return True


async def check_feeds_once(on_new_entry):
    """
    Checks every stored RSS feed for entries newer than last_seen_link.
    `on_new_entry(user_id, entry)` is awaited for each new matching entry,
    where entry has .title and a magnet/link.
    """
    feeds = db.list_rss_feeds()
    for feed_row in feeds:
        try:
            parsed = feedparser.parse(feed_row["feed_url"])
        except Exception as e:
            logger.warning(f"Failed to fetch RSS feed {feed_row['feed_url']}: {e}")
            continue

        if not parsed.entries:
            continue

        new_entries = []
        for entry in parsed.entries:
            link = entry.get("link", "")
            if link == feed_row["last_seen_link"]:
                break  # reached previously-seen entry; everything after is old
            if _entry_matches(entry.get("title", ""), feed_row["filter_include"], feed_row["filter_exclude"]):
                new_entries.append(entry)

        if new_entries:
            # process oldest-first so delivery order matches release order
            for entry in reversed(new_entries):
                await on_new_entry(feed_row["user_id"], entry)

            db.update_last_seen(feed_row["id"], parsed.entries[0].get("link", ""))


async def rss_loop(on_new_entry):
    while True:
        await check_feeds_once(on_new_entry)
        await asyncio.sleep(config.RSS_CHECK_INTERVAL_SECONDS)
