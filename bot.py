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
        print('[bootstrap] installing Python requirements...')
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-q', '-r', os.path.join(_HERE, 'requirements.txt')],
            check=True,
        )


def _ensure_system_packages():
    missing = [b for b in ('aria2c', 'ffmpeg') if shutil.which(b) is None]
    if not missing:
        return
    print(f'[bootstrap] installing system packages: {missing}')
    subprocess.run(['sudo', 'apt-get', 'update'])
    subprocess.run(['sudo', 'apt-get', 'install', '-y', 'aria2', 'ffmpeg'])
    still_missing = [b for b in missing if shutil.which(b) is None]
    if still_missing:
        print(f'[bootstrap] WARNING: could not install {still_missing} automatically; '
              f'install them manually if leech/compress fail.')


def _start_aria2_daemon():
    if shutil.which('aria2c') is None:
        return
    secret = os.environ.get('ARIA2_SECRET') or secrets.token_urlsafe(48)
    os.environ['ARIA2_SECRET'] = secret
    log_path = os.path.join(_HERE, 'aria2.log')
    log = open(log_path, 'a')
    subprocess.Popen(
        ['aria2c', '--enable-rpc=true', f'--rpc-secret={secret}', '-j5', '-x5'],
        stdout=log, stderr=log,
    )
    time.sleep(2)  # give the RPC daemon a moment to come up


_ensure_python_deps()
_ensure_system_packages()
_start_aria2_daemon()

import asyncio
import logging
import traceback

from pyrogram import idle

from lazyleech import app, ADMIN_CHATS, STARTUP_CHANNEL, preserved_logs
from lazyleech.utils.upload_worker import upload_worker

logging.basicConfig(level=logging.INFO)
logging.getLogger('pyrogram.syncer').setLevel(logging.WARNING)


async def _send_startup_message():
    me = await app.get_me()
    text = f'✅ <b>{me.first_name}</b> is now online and ready to leech.'
    if STARTUP_CHANNEL:
        try:
            await app.send_message(STARTUP_CHANNEL, text)
        except Exception:
            logging.exception('Failed to send startup message to STARTUP_CHANNEL (%s)', STARTUP_CHANNEL)
    for i in ADMIN_CHATS:
        try:
            await app.send_message(i, text)
        except Exception:
            logging.exception('Failed to send startup message to admin chat %s', i)


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
    await _send_startup_message()
    await idle()
    await app.stop()


if __name__ == '__main__':
    app.loop.run_until_complete(main())
