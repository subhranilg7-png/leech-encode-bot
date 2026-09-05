# Filename metadata parser for auto-rename.
# Detects season, episode, and quality from a source filename so the
# auto-rename template can fill them in.

import re

SEASON_EPISODE_PATTERNS = [
    re.compile(r'[Ss](?P<season>\d{1,2})[\s._-]?[Ee](?P<episode>\d{1,3})'),   # S01E02 / S01 E02
    re.compile(r'[Ss](?P<season>\d{1,2})\s*-\s*(?P<episode>\d{1,3})'),        # S1 - 01
    re.compile(r'\[(?P<episode>\d{1,3})\s*-'),                                # [04 -
    re.compile(r'Season\s*(?P<season>\d{1,2})[^\d]+(?P<episode>\d{1,3})', re.IGNORECASE),  # Season 2 ... 05
    re.compile(r'[Ee]pisode\s*(?P<episode>\d{1,3})', re.IGNORECASE),
    re.compile(r'(?<![\d])(?P<episode>\d{2,3})(?![\d])'),                     # bare "- 07 -" fallback
]

QUALITY_PATTERN = re.compile(r'(?P<quality>480p|720p|1080p|2160p|4k)', re.IGNORECASE)


def parse_filename(name):
    """Returns a dict with season, episode, quality (any may be None)."""
    result = {'season': None, 'episode': None, 'quality': None}

    for pattern in SEASON_EPISODE_PATTERNS:
        m = pattern.search(name)
        if m:
            gd = m.groupdict()
            if gd.get('episode') and not result['episode']:
                result['episode'] = gd['episode'].zfill(2)
            if gd.get('season') and not result['season']:
                result['season'] = gd['season'].zfill(2)
            if result['episode']:
                break

    # [SO] tag present with no detected season defaults to season 1
    if result['episode'] and not result['season']:
        if re.search(r'\[SO\]', name, re.IGNORECASE):
            result['season'] = '01'

    qm = QUALITY_PATTERN.search(name)
    if qm:
        result['quality'] = qm.group('quality').lower()

    return result


_TAG_STRIP = re.compile(r'\s*(?:\[.+?\]|\(.+?\))\s*')


def build_filename(template, original_name, parsed):
    """Fill a user template with parsed metadata + original extension."""
    import os
    ext = os.path.splitext(original_name)[1]
    raw_title = original_name[: len(original_name) - len(ext)] if ext else original_name
    title = _TAG_STRIP.sub(' ', raw_title).replace('.', ' ').replace('_', ' ')
    title = re.sub(r'\s+', ' ', title).strip() or raw_title
    values = {
        'title': title,
        'season': parsed.get('season') or '01',
        'episode': parsed.get('episode') or '00',
        'quality': parsed.get('quality') or '',
        'ext': ext.lstrip('.'),
    }
    try:
        name = template.format(**values)
    except (KeyError, IndexError):
        name = title
    if ext and not name.lower().endswith(ext.lower()):
        name += ext
    return name
