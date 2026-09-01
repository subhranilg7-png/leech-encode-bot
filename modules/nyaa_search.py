"""
Search nyaa.si using its built-in RSS endpoint (no scraping/HTML parsing needed).
Docs: https://nyaa.si/?page=rss&q=<query>&c=<category>&f=<filter>
"""

import feedparser
import requests

import config


def search_nyaa(query: str, limit: int = 10, trusted_only: bool = False):
    """
    Returns a list of dicts: [{title, link, magnet, size, seeders, leechers, published}, ...]
    `link` is the nyaa.si page; the magnet is extracted from the RSS entry.
    """
    params = {"page": "rss", "q": query}
    if trusted_only:
        params["f"] = "2"  # nyaa's "trusted only" filter

    resp = requests.get(config.NYAA_BASE_URL, params=params, timeout=15)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    results = []
    for entry in feed.entries[:limit]:
        results.append({
            "title": entry.get("title", "Unknown"),
            "link": entry.get("link", ""),
            "magnet": entry.get("nyaa_magneturi") or entry.get("link", ""),
            "size": entry.get("nyaa_size", "?"),
            "seeders": entry.get("nyaa_seeders", "?"),
            "leechers": entry.get("nyaa_leechers", "?"),
            "published": entry.get("published", ""),
        })
    return results


def format_results(results):
    """Human-readable numbered list for a Telegram message."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(
            f"{i}. {r['title']}\n"
            f"   Size: {r['size']} | Seeders: {r['seeders']} | Leechers: {r['leechers']}"
        )
    return "\n".join(lines)
