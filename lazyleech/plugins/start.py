# lazyleech - start menu
#
# Proper inline-button home menu (reference: Awakener-bots/encode-bot and
# abhinai2244/ENCODING-BOT's /start + /settings interfaces) instead of a
# wall of plain text. Ties together nyaa/magnet leech, direct-compress,
# rename, thumbnail, metadata, and encode settings from one place.

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .. import ALL_CHATS
from ..utils.db import get_settings, set_setting
from .encsettings import _build_menu as _encode_menu, _summary_text as _encode_summary

HOME_TEXT = (
    "<b>Hi, I'm your leech + encode bot.</b>\n\n"
    "• Send a <b>magnet link</b>, <b>.torrent file</b>, or use /nyaa to search nyaa.si and leech a result\n"
    "• Send me a <b>video file directly</b> to have it compressed/renamed/thumbnailed (if enabled below)\n\n"
    "Tap a button to configure that feature."
)

TOGGLE_FIELD_TO_PANEL = {
    'auto_rename_enabled': 'rename',
    'compress_enabled': 'compress',
    'metadata_enabled': 'metadata',
}


def _home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⚙️ Encode Settings', callback_data='menu:encset'),
         InlineKeyboardButton('✏️ Rename', callback_data='menu:rename')],
        [InlineKeyboardButton('🖼 Thumbnail', callback_data='menu:thumb'),
         InlineKeyboardButton('📦 Direct Compress', callback_data='menu:compress')],
        [InlineKeyboardButton('🏷 Metadata', callback_data='menu:metadata'),
         InlineKeyboardButton('📊 My Settings', callback_data='menu:mysettings')],
        [InlineKeyboardButton('❓ Help', callback_data='menu:help')],
    ])


def _back_kb(extra=None):
    rows = list(extra) if extra else []
    rows.append([InlineKeyboardButton('🔙 Back', callback_data='menu:home')])
    return InlineKeyboardMarkup(rows)


async def _panel_rename(user_id):
    s = await get_settings(user_id)
    text = (
        '<b>Auto-rename</b>\n'
        f"Status: <code>{'ON' if s['auto_rename_enabled'] else 'OFF'}</code>\n"
        f"Template: <code>{s['rename_format'] or 'not set'}</code>\n\n"
        'Set a template with:\n/setrenameformat {title} S{season}E{episode} [{quality}]'
    )
    kb = _back_kb([[InlineKeyboardButton(
        f"Turn {'OFF' if s['auto_rename_enabled'] else 'ON'}",
        callback_data='menu:toggle:auto_rename_enabled'
    )]])
    return text, kb


async def _panel_compress(user_id):
    s = await get_settings(user_id)
    text = (
        '<b>Direct-file compression</b>\n'
        f"Status: <code>{'ON' if s['compress_enabled'] else 'OFF'}</code>\n\n"
        'When ON, any video/audio file you send the bot directly gets compressed, '
        'renamed, thumbnailed, and metadata-tagged the same way as a leech.\n'
        'Configure quality via ⚙️ Encode Settings.'
    )
    kb = _back_kb([[InlineKeyboardButton(
        f"Turn {'OFF' if s['compress_enabled'] else 'ON'}",
        callback_data='menu:toggle:compress_enabled'
    )]])
    return text, kb


async def _panel_metadata(user_id):
    s = await get_settings(user_id)
    text = (
        '<b>Metadata title tag</b>\n'
        f"Status: <code>{'ON' if s['metadata_enabled'] else 'OFF'}</code>\n"
        f"Template: <code>{s['metadata_template']}</code>\n\n"
        'Embeds a title into the file itself (shows up in media players), independent '
        'of the on-disk filename. Set a template with:\n'
        '/setmetadataformat {title} S{season}E{episode}'
    )
    kb = _back_kb([[InlineKeyboardButton(
        f"Turn {'OFF' if s['metadata_enabled'] else 'ON'}",
        callback_data='menu:toggle:metadata_enabled'
    )]])
    return text, kb


async def _panel_thumb(user_id):
    text = (
        '<b>Thumbnail</b>\n\n'
        'Reply to any photo with /thumbnail (or /t) to save it as your persistent '
        'thumbnail - applied to every leech and every direct-compressed file.'
    )
    return text, _back_kb()


async def _panel_mysettings(user_id):
    s = await get_settings(user_id)
    text = (
        '<b>Your settings</b>\n'
        f"Auto-rename: {'ON' if s['auto_rename_enabled'] else 'OFF'}\n"
        f"Rename format: <code>{s['rename_format'] or 'not set'}</code>\n"
        f"Direct-file compression: {'ON' if s['compress_enabled'] else 'OFF'}\n"
        f"Metadata title: {'ON' if s['metadata_enabled'] else 'OFF'} (<code>{s['metadata_template']}</code>)\n"
    )
    kb = _back_kb([[InlineKeyboardButton('⚙️ Encode Settings', callback_data='menu:encset')]])
    return text, kb


async def _panel_help(user_id):
    text = 'Use /help in chat for the full command reference, or tap Back to keep configuring from here.'
    return text, _back_kb()


async def _panel_encset(user_id):
    s = await get_settings(user_id)
    return _encode_summary(s), _encode_menu(s)


PANELS = {
    'rename': _panel_rename,
    'compress': _panel_compress,
    'metadata': _panel_metadata,
    'thumb': _panel_thumb,
    'mysettings': _panel_mysettings,
    'help': _panel_help,
    'encset': _panel_encset,
}


@Client.on_message(filters.private & filters.command('start'))
async def start_cmd(client, message):
    await message.reply_text(HOME_TEXT, reply_markup=_home_kb())


@Client.on_callback_query(filters.regex(r'^menu:'))
async def menu_callback(client, callback_query):
    message = callback_query.message
    reply_to = message.reply_to_message
    owner_id = (reply_to.from_user.id if reply_to and reply_to.from_user else None) or callback_query.from_user.id
    if callback_query.from_user.id != owner_id:
        await callback_query.answer("This isn't your menu.", show_alert=True)
        return

    user_id = callback_query.from_user.id
    parts = callback_query.data.split(':', 2)
    action = parts[1]
    await callback_query.answer()

    if action == 'home':
        await message.edit_text(HOME_TEXT, reply_markup=_home_kb())
        return

    if action == 'toggle' and len(parts) > 2:
        field = parts[2]
        current = (await get_settings(user_id))[field]
        await set_setting(user_id, field, not current)
        action = TOGGLE_FIELD_TO_PANEL.get(field, 'home')

    panel = PANELS.get(action)
    if not panel:
        return
    text, kb = await panel(user_id)
    await message.edit_text(text, reply_markup=kb)
