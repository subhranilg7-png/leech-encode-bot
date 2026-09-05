# Compression helper - 3 fixed quality presets, x264 + aac.
# Only re-encodes to the ONE selected quality (never all three).

import os
import asyncio

# height, crf, audio bitrate
QUALITY_PRESETS = {
    '480p': (480, 28, '96k'),
    '720p': (720, 26, '128k'),
    '1080p': (1080, 24, '160k'),
}


async def compress_video(filepath, quality, out_dir):
    if quality not in QUALITY_PRESETS:
        quality = '720p'
    height, crf, abitrate = QUALITY_PRESETS[quality]
    name, ext = os.path.splitext(os.path.basename(filepath))
    out_path = os.path.join(out_dir, f'{name} [{quality}]{ext or ".mkv"}')

    cmd = [
        'ffmpeg', '-y', '-i', filepath,
        '-map', '0',
        '-vf', f"scale=-2:'min({height},ih)'",
        '-c:v', 'libx264', '-crf', str(crf), '-preset', 'fast',
        '-c:a', 'aac', '-b:a', abitrate,
        '-c:s', 'copy',
        out_path,
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError(f'ffmpeg compression failed: {stderr.decode(errors="ignore")[-2000:]}')
    return out_path
