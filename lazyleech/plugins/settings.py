from pyrogram import Client, filters

from .. import ALL_CHATS, help_dict
from ..utils.db import get_settings, set_setting


@Client.on_message(filters.command('autorename') & filters.chat(ALL_CHATS))
async def toggle_autorename(client, message):
    args = message.text.split(None, 1)
    user_id = message.from_user.id
    if len(args) < 2 or args[1].lower() not in ('on', 'off'):
        current = await get_settings(user_id)
        await message.reply_text(
            f"Auto-rename is currently <b>{'ON' if current['auto_rename_enabled'] else 'OFF'}</b>.\n"
            f"Usage: /autorename on|off"
        )
        return
    enabled = args[1].lower() == 'on'
    await set_setting(user_id, 'auto_rename_enabled', enabled)
    await message.reply_text(f"Auto-rename turned <b>{'ON' if enabled else 'OFF'}</b>.")


@Client.on_message(filters.command('setrenameformat') & filters.chat(ALL_CHATS))
async def set_rename_format(client, message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        await message.reply_text(
            'Usage: /setrenameformat {title} S{season}E{episode} [{quality}]\n'
            'Placeholders: {title} {season} {episode} {quality} {ext}'
        )
        return
    await set_setting(message.from_user.id, 'rename_format', args[1])
    await message.reply_text('Rename format saved.')


@Client.on_message(filters.command(['togglecompress', 'compress']) & filters.chat(ALL_CHATS))
async def toggle_compress(client, message):
    args = message.text.split(None, 1)
    user_id = message.from_user.id
    if len(args) < 2 or args[1].lower() not in ('on', 'off'):
        current = await get_settings(user_id)
        await message.reply_text(
            f"Direct-file compression is currently <b>{'ON' if current['compress_enabled'] else 'OFF'}</b>.\n"
            f"Usage: /togglecompress on|off"
        )
        return
    enabled = args[1].lower() == 'on'
    await set_setting(user_id, 'compress_enabled', enabled)
    await message.reply_text(f"Direct-file compression turned <b>{'ON' if enabled else 'OFF'}</b>.")


@Client.on_message(filters.command(['togglemetadata', 'metadata']) & filters.chat(ALL_CHATS))
async def toggle_metadata(client, message):
    args = message.text.split(None, 1)
    user_id = message.from_user.id
    if len(args) < 2 or args[1].split(None, 1)[0].lower() not in ('on', 'off'):
        current = await get_settings(user_id)
        await message.reply_text(
            f"Metadata title tagging is currently <b>{'ON' if current['metadata_enabled'] else 'OFF'}</b>.\n"
            f"Template: <code>{current['metadata_template']}</code>\n"
            f"Usage: /togglemetadata on|off\n"
            f"/setmetadataformat &lt;template&gt; - placeholders: {{title}} {{season}} {{episode}} {{quality}}"
        )
        return
    enabled = args[1].split(None, 1)[0].lower() == 'on'
    await set_setting(user_id, 'metadata_enabled', enabled)
    await message.reply_text(f"Metadata title tagging turned <b>{'ON' if enabled else 'OFF'}</b>.")


@Client.on_message(filters.command('setmetadataformat') & filters.chat(ALL_CHATS))
async def set_metadata_format(client, message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        await message.reply_text(
            'Usage: /setmetadataformat {title} S{season}E{episode}\n'
            'Placeholders: {title} {season} {episode} {quality}'
        )
        return
    await set_setting(message.from_user.id, 'metadata_template', args[1])
    await message.reply_text('Metadata title template saved.')


@Client.on_message(filters.command(['mysettings', 'settings']) & filters.chat(ALL_CHATS))
async def show_settings(client, message):
    s = await get_settings(message.from_user.id)
    await message.reply_text(
        '<b>Your settings</b>\n'
        f"Auto-rename: {'ON' if s['auto_rename_enabled'] else 'OFF'}\n"
        f"Rename format: <code>{s['rename_format'] or 'not set'}</code>\n"
        f"Direct-file compression: {'ON' if s['compress_enabled'] else 'OFF'}\n"
        f"Metadata title: {'ON' if s['metadata_enabled'] else 'OFF'} (<code>{s['metadata_template']}</code>)\n"
        f"Encode settings: use /encsettings to view or change them"
    )


help_dict['settings'] = ('Rename & Compression Settings', '''
/autorename on|off - toggle auto-rename for leeched/uploaded files
/setrenameformat &lt;template&gt; - set the auto-rename template
/togglecompress on|off - toggle compression for files sent directly to the bot
/togglemetadata on|off - toggle embedding a metadata title tag in the file
/setmetadataformat &lt;template&gt; - set the metadata title template
/encsettings - interactive panel for codec/CRF/preset/10-bit/resolution/audio
/mysettings - show your current settings
''')
