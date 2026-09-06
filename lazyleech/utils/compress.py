# Encoding engine - builds an ffmpeg command from a user's per-user encode
# settings (utils/db.py: encode_format/codec/crf/preset/10bit/resolution/
# audio_*) instead of a fixed 480p/720p/1080p-only preset table.

import os
import asyncio

RESOLUTIONS = {
    'original': None,
    '1080p': 1080,
    '720p': 720,
    '540p': 540,
    '480p': 480,
    '360p': 360,
}

CODEC_ENCODERS = {
    'h264': 'libx264',
    'h265': 'libx265',
}

AUDIO_ENCODERS = {
    'copy': 'copy',
    'aac': 'aac',
    'ac3': 'ac3',
    'opus': 'libopus',
    'mp3': 'libmp3lame',
}

AUDIO_CHANNELS = {
    'original': None,
    'mono': 1,
    'stereo': 2,
    '5.1': 6,
}

VALID_PRESETS = (
    'ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
    'medium', 'slow', 'slower', 'veryslow',
)

CONTAINER_EXT = {'mkv': '.mkv', 'mp4': '.mp4', 'avi': '.avi'}


def _build_cmd(filepath, settings, out_path, *, include_attachments, include_subs, metadata_title=None):
    codec = settings.get('encode_codec', 'h264')
    if codec not in CODEC_ENCODERS:
        codec = 'h264'
    encoder = CODEC_ENCODERS[codec]

    preset = settings.get('encode_preset', 'fast')
    if preset not in VALID_PRESETS:
        preset = 'fast'

    crf = settings.get('encode_crf', 26)
    try:
        crf = int(crf)
    except (TypeError, ValueError):
        crf = 26

    ten_bit = bool(settings.get('encode_10bit')) and codec == 'h265'

    resolution = settings.get('encode_resolution', 'original')
    height = RESOLUTIONS.get(resolution)

    audio_codec = settings.get('encode_audio_codec', 'aac')
    if audio_codec not in AUDIO_ENCODERS:
        audio_codec = 'aac'
    audio_encoder = AUDIO_ENCODERS[audio_codec]
    audio_bitrate = settings.get('encode_audio_bitrate', '128k')
    channels = AUDIO_CHANNELS.get(settings.get('encode_audio_channels', 'original'))

    if include_attachments:
        maps = ['-map', '0']
    else:
        maps = ['-map', '0:v', '-map', '0:a']
        if include_subs:
            maps += ['-map', '0:s?']

    cmd = ['ffmpeg', '-y', '-i', filepath, *maps]

    if height:
        cmd += ['-vf', f"scale=-2:'min({height},ih)'"]

    cmd += ['-c:v', encoder, '-crf', str(crf), '-preset', preset]
    if ten_bit:
        cmd += ['-pix_fmt', 'yuv420p10le']

    if audio_encoder == 'copy':
        cmd += ['-c:a', 'copy']
    else:
        cmd += ['-c:a', audio_encoder, '-b:a', audio_bitrate]
        if channels:
            cmd += ['-ac', str(channels)]

    if include_subs:
        cmd += ['-c:s', 'copy']
    if include_attachments:
        cmd += ['-c:t', 'copy']  # font/attachment streams - anime mkv releases almost always have these
    if metadata_title:
        cmd += ['-metadata', f'title={metadata_title}']

    cmd.append(out_path)
    return cmd


async def _run(cmd):
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()
    return proc.returncode, stderr.decode(errors='ignore')


async def compress_video(filepath, settings, out_dir, metadata_title=None):
    """settings: the per-user settings dict from utils.db.get_settings()."""
    ext = CONTAINER_EXT.get(settings.get('encode_format', 'mkv'), '.mkv')
    name = os.path.splitext(os.path.basename(filepath))[0]
    codec_tag = settings.get('encode_codec', 'h264').upper()
    res_tag = settings.get('encode_resolution', 'original')
    tag = f'{res_tag}' if res_tag == 'original' else res_tag
    out_path = os.path.join(out_dir, f'{name} [{tag}-{codec_tag}]{ext}')

    cmd = _build_cmd(filepath, settings, out_path, include_attachments=True, include_subs=True, metadata_title=metadata_title)
    returncode, stderr = await _run(cmd)
    if returncode != 0 or not os.path.isfile(out_path):
        # Fallback 1: drop attachments (fonts) but keep subs - covers the
        # common anime-mkv case where -c:t copy still isn't enough (e.g.
        # target container can't hold the attachment codec at all, such as
        # encoding out to mp4).
        cmd = _build_cmd(filepath, settings, out_path, include_attachments=False, include_subs=True, metadata_title=metadata_title)
        returncode, stderr = await _run(cmd)
    if returncode != 0 or not os.path.isfile(out_path):
        # Fallback 2: drop subs too rather than silently uploading the
        # original with no explanation.
        cmd = _build_cmd(filepath, settings, out_path, include_attachments=False, include_subs=False, metadata_title=metadata_title)
        returncode, stderr = await _run(cmd)
    if returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError(f'ffmpeg encoding failed: {stderr[-2000:]}')
    return out_path


async def apply_metadata_only(filepath, metadata_title, out_dir):
    """Fast stream-copy remux to embed a metadata title with no re-encode -
    used when compression is off but the user still wants the title tag set."""
    ext = os.path.splitext(filepath)[1] or '.mkv'
    name = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(out_dir, f'{name}{ext}')
    cmd = [
        'ffmpeg', '-y', '-i', filepath,
        '-map', '0', '-c', 'copy',
        '-metadata', f'title={metadata_title}',
        out_path,
    ]
    returncode, stderr = await _run(cmd)
    if returncode != 0 or not os.path.isfile(out_path):
        # Attachment streams again being the likely culprit - retry without them.
        cmd = [
            'ffmpeg', '-y', '-i', filepath,
            '-map', '0:v', '-map', '0:a', '-map', '0:s?', '-c', 'copy',
            '-metadata', f'title={metadata_title}',
            out_path,
        ]
        returncode, stderr = await _run(cmd)
    if returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError(f'ffmpeg metadata remux failed: {stderr[-2000:]}')
    return out_path
