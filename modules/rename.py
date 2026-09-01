import os
import re

# Reused/expanded from the Auto-Rename-Bot pattern set: covers "S1 - 01",
# "[04 -", "Season 2", plain "- 01", and "EP01" style tags.
EPISODE_PATTERNS = [
    re.compile(r"[Ss](\d{1,2})\s*-\s*(\d{1,3})"),          # S1 - 01
    re.compile(r"\[(\d{1,3})\s*-"),                          # [04 -
    re.compile(r"[Ss]eason\s*(\d{1,2}).*?(\d{1,3})", re.I),  # Season 2 ... 05
    re.compile(r"-\s*(\d{1,3})\s*(?:\[|\(|$)"),               # - 01 [1080p]
    re.compile(r"[Ee][Pp]?(\d{1,3})"),                        # EP01 / E01
]

QUALITY_PATTERN = re.compile(r"(480p|720p|1080p|2160p|4k)", re.I)


def detect_episode_season(filename: str):
    """
    Returns (season, episode) as strings, or (None, None) if nothing matched.
    Domain rule carried over from Auto-Rename-Bot: an [SO] tag with no
    detected season number defaults to season 1.
    """
    season, episode = None, None

    for pattern in EPISODE_PATTERNS:
        match = pattern.search(filename)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                season, episode = groups
            elif len(groups) == 1:
                episode = groups[0]
            break

    if episode and not season:
        # [SO]-style tag present with no season detected -> default season 1
        if re.search(r"\[SO\]|\bSO\b", filename, re.I):
            season = "1"
        else:
            season = "1"  # same default applies generally per prior bot's rule

    return season, episode


def detect_quality(filename: str):
    match = QUALITY_PATTERN.search(filename)
    return match.group(1) if match else None


def auto_rename(file_path: str, template: str = "{title} - S{season}E{episode} [{quality}]") -> str:
    """
    Detects season/episode/quality from the current filename and renames
    the file using the given template. Falls back gracefully if fields
    are missing.
    """
    directory = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    name_no_ext, ext = os.path.splitext(base_name)

    season, episode = detect_episode_season(name_no_ext)
    quality = detect_quality(name_no_ext) or "unknown"

    if not episode:
        # Detection failed -> caller should fall back to manual rename
        raise ValueError("Could not auto-detect episode info; fall back to manual rename.")

    # Best-effort title = everything before the first bracket/dash cluster
    title_guess = re.split(r"\[|\(|-\s*\d", name_no_ext)[0].strip() or "Episode"

    new_name = template.format(
        title=title_guess,
        season=season or "1",
        episode=episode.zfill(2),
        quality=quality,
    ) + ext

    new_path = os.path.join(directory, new_name)
    os.rename(file_path, new_path)
    return new_path


def manual_rename(file_path: str, new_full_name: str) -> str:
    """
    User supplies the complete desired filename in one message.
    No separate episode/season/quality prompts. Extension is preserved
    from the source file if the user didn't include one.
    """
    directory = os.path.dirname(file_path)
    original_ext = os.path.splitext(file_path)[1]  # includes the dot, e.g. ".mkv"

    new_full_name = new_full_name.strip()
    if not os.path.splitext(new_full_name)[1]:
        new_full_name += original_ext

    new_path = os.path.join(directory, new_full_name)
    os.rename(file_path, new_path)
    return new_path
