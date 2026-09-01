import asyncio
import os

import config

RESOLUTION_HEIGHTS = {
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
}


async def encode_video(input_path: str, resolution: str = None, codec: str = None, crf: str = None) -> str:
    """
    Runs FFmpeg to resize + re-encode/compress a video.
    Returns the path to the encoded output file.
    """
    resolution = resolution or config.DEFAULT_RESOLUTION
    codec = codec or config.DEFAULT_CODEC
    crf = crf or config.DEFAULT_CRF

    height = RESOLUTION_HEIGHTS.get(resolution, 1080)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(config.ENCODE_DIR, f"{base_name}_{resolution}.mkv")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"scale=-2:{height}",
        "-c:v", codec,
        "-crf", str(crf),
        "-preset", config.DEFAULT_PRESET,
        "-c:a", "copy",
        "-c:s", "copy",
        output_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg encode failed:\n{stderr.decode(errors='ignore')[-1500:]}")

    if not os.path.exists(output_path):
        raise RuntimeError("FFmpeg reported success but output file is missing.")

    return output_path
