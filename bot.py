#!/usr/bin/env python3
"""
Entrypoint - run with either: python bot.py   OR   sh run.sh
Both do the same thing. This file self-installs everything it needs
(Python packages, ffmpeg/aria2, and the aria2c RPC daemon) on every
run, so there's no separate manual setup step required.
"""

import os
import sys
import time
import shutil
import secrets
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))


def _ensure_python_deps():
    try:
        import pyrogram, aiohttp, motor, bs4, feedparser  # noqa: F401
        from PIL import Image  # noqa: F401
        import lxml.html.clean  # noqa: F401
    except ImportError:
        print('[bootstrap] installing Python requirements (this can take a while on a slow connection)...')
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install',
            '--retries', '10', '--timeout', '120',
            '-r', os.path.join(_HERE, 'requirements.txt'),
        ])
        if result.returncode != 0:
            print('[bootstrap] WARNING: pip install exited non-zero (see output above - often a slow/dropped '
                  'connection). Retrying once more...')
            subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                '--retries', '10', '--timeout', '120',
                '-r', os.path.join(_HERE, 'requirements.txt'),
            ])


_LOCAL_BIN = os.path.join(_HERE, 'bin')
_STATIC_FFMPEG_URL = 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz'


def _install_apt_package(name):
    """Install a single apt package on its own, so one broken package
    elsewhere on the mirror can't block this one."""
    subprocess.run(['sudo', 'apt-get', 'install', '-y', '--no-install-recommends', '--fix-missing', name])


def _download_static_ffmpeg():
    """Fallback when the Debian ffmpeg package (or its deps) 404 on the
    mirror: grab a self-contained static build instead, no apt involved."""
    if shutil.which('ffmpeg'):
        return
    print('[bootstrap] apt ffmpeg unavailable, downloading a static ffmpeg build instead...')
    try:
        import urllib.request
        import tarfile
        os.makedirs(_LOCAL_BIN, exist_ok=True)
        archive_path = os.path.join(_HERE, 'ffmpeg-static.tar.xz')
        urllib.request.urlretrieve(_STATIC_FFMPEG_URL, archive_path)
        with tarfile.open(archive_path) as tar:
            for member in tar.getmembers():
                if member.name.endswith(('/ffmpeg', '/ffprobe')):
                    member.name = os.path.basename(member.name)
                    tar.extract(member, path=_LOCAL_BIN)
        os.remove(archive_path)
        for b in ('ffmpeg', 'ffprobe'):
            p = os.path.join(_LOCAL_BIN, b)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
        print('[bootstrap] static ffmpeg installed to', _LOCAL_BIN)
    except Exception as ex:
        print(f'[bootstrap] WARNING: static ffmpeg download failed ({ex}); compression will not work.')


def _ensure_system_packages():
    os.environ['PATH'] = _LOCAL_BIN + os.pathsep + os.environ.get('PATH', '')
    if shutil.which('aria2c') and shutil.which('ffmpeg'):
        return
    print('[bootstrap] installing system packages...')
    subprocess.run(['sudo', 'apt-get', 'update'])
    if not shutil.which('aria2c'):
        _install_apt_package('aria2')
    if not shutil.which('ffmpeg'):
        _install_apt_package('ffmpeg')
    if not shutil.which('ffmpeg'):
        _download_static_ffmpeg()
    still_missing = [b for b in ('aria2c', 'ffmpeg') if shutil.which(b) is None]
    if still_missing:
        print(f'[bootstrap] WARNING: still missing {still_missing}; install manually if leech/compress fail.')


def _aria2_rpc_alive(secret):
    """Return True if something is already answering RPC on 6800 with this secret."""
    import json
    import urllib.request
    payload = json.dumps({
        'jsonrpc': '2.0', 'id': 'boot-check', 'method': 'aria2.getVersion',
        'params': ([f'token:{secret}'] if secret else []),
    }).encode()
    try:
        req = urllib.request.Request('http://127.0.0.1:6800/jsonrpc', data=payload, method='POST')
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read())
        return 'result' in body
    except Exception:
        return False


def _kill_stale_aria2():
    """Kill any aria2c process left over from a previous run (mismatched secret,
    port 6800 already bound) so the daemon we start below actually owns the port."""
    subprocess.run(['pkill', '-f', 'aria2c --enable-rpc'], stderr=subprocess.DEVNULL)
    time.sleep(1)


def _start_aria2_daemon():
    if shutil.which('aria2c') is None:
        return
    secret = os.environ.get('ARIA2_SECRET') or secrets.token_urlsafe(48)
    os.environ['ARIA2_SECRET'] = secret
    if _aria2_rpc_alive(secret):
        print('[bootstrap] aria2 RPC already up and authenticating fine, reusing it.')
        return
    # Either nothing is running, or something is running with a stale/different
    # secret (leftover from a previous run) - clear it so we don't end up with
    # two daemons disagreeing about the secret while only one owns the port.
    _kill_stale_aria2()
    log_path = os.path.join(_HERE, 'aria2.log')
    log = open(log_path, 'a')
    subprocess.Popen(
        ['aria2c', '--enable-rpc=true', f'--rpc-secret={secret}', '-j5', '-x5'],
        stdout=log, stderr=log,
    )
    time.sleep(2)  # give the RPC daemon a moment to come up
    if not _aria2_rpc_alive(secret):
        print('[bootstrap] WARNING: aria2 RPC did not come up cleanly - check aria2.log')


_ensure_python_deps()
_ensure_system_packages()
_start_aria2_daemon()

import asyncio
import logging
import traceback

from pyrogram import idle
from pyrogram.types import BotCommand

from lazyleech import app, ADMIN_CHATS, preserved_logs
from lazyleech.utils.upload_worker import upload_worker

logging.basicConfig(level=logging.INFO)
logging.getLogger('pyrogram.syncer').setLevel(logging.WARNING)


BOT_COMMANDS = [
    BotCommand('start', 'Say hi / check the bot is alive'),
    BotCommand('help', 'Full command reference'),
    BotCommand('torrent', 'Leech a magnet link or .torrent file'),
    BotCommand('directdl', 'Leech a direct download link'),
    BotCommand('nyaa', 'Search nyaa.si and leech a result'),
    BotCommand('list', 'Show your active leeches'),
    BotCommand('cancel', 'Cancel a running leech'),
    BotCommand('autorename', 'Turn auto-rename on/off'),
    BotCommand('setrenameformat', 'Set the auto-rename template'),
    BotCommand('togglecompress', 'Turn direct-file compression on/off'),
    BotCommand('togglemetadata', 'Turn metadata title tagging on/off'),
    BotCommand('setmetadataformat', 'Set the metadata title template'),
    BotCommand('encsettings', 'Open the encode-settings panel (codec/CRF/preset/resolution/audio)'),
    BotCommand('mysettings', 'Show your current settings'),
    BotCommand('thumbnail', 'Set a persistent thumbnail'),
    BotCommand('watermark', 'Set a persistent watermark'),
    BotCommand('mediainfo', 'Post detailed media info to Telegraph'),
]


async def main():
    async def _autorestart_worker():
        while True:
            try:
                await upload_worker()
            except Exception as ex:
                preserved_logs.append(ex)
                logging.exception('upload worker committed suicide')
                tb = traceback.format_exc()
                for i in ADMIN_CHATS:
                    try:
                        await app.send_message(i, 'upload worker committed suicide')
                        await app.send_message(i, tb, parse_mode=None)
                    except Exception:
                        logging.exception('failed %s', i)

    asyncio.create_task(_autorestart_worker())
    await app.start()
    try:
        await app.set_bot_commands(BOT_COMMANDS)
    except Exception:
        logging.exception('Failed to register bot command menu (non-fatal)')
    await idle()
    await app.stop()


if __name__ == '__main__':
    app.loop.run_until_complete(main())
