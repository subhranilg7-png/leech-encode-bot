#!/usr/bin/env python3
"""
Entrypoint - run with: python bot.py
(Replaces `python -m lazyleech`; kept as a thin wrapper so Codespaces/Procfile
setups can point at a single top-level file.)
"""

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
