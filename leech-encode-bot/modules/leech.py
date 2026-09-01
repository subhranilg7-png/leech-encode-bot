"""
Leeches a torrent/magnet using aria2c's JSON-RPC interface.
Requires aria2c running with --enable-rpc, e.g.:
    aria2c --enable-rpc --rpc-listen-all=false --rpc-secret=<secret> -D
"""

import asyncio
import os

import aria2p

import config

aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=config.ARIA2_RPC_SECRET,
    )
)


async def leech_magnet(magnet_or_url: str, progress_callback=None) -> str:
    """
    Adds a magnet/torrent link to aria2, waits for completion, returns the
    path to the downloaded file (largest file if it's a multi-file torrent).
    """
    if magnet_or_url.startswith("magnet:"):
        download = aria2.add_magnet(magnet_or_url, options={"dir": config.DOWNLOAD_DIR})
    else:
        download = aria2.add_uris([magnet_or_url], options={"dir": config.DOWNLOAD_DIR})

    gid = download.gid

    while True:
        await asyncio.sleep(3)
        download = aria2.get_download(gid)

        if progress_callback:
            await progress_callback(download.progress, download.download_speed_string())

        if download.is_complete:
            break
        if download.has_failed:
            raise RuntimeError(f"Leech failed: {download.error_message}")

    # If it's a torrent with multiple files, pick the largest media file
    files = [f.path for f in download.files if os.path.exists(f.path)]
    if not files:
        raise RuntimeError("No files found after download completed.")

    largest = max(files, key=lambda p: os.path.getsize(p))
    return largest
