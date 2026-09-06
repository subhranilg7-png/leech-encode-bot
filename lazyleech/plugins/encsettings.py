# Interactive encode-settings panel - replaces the old fixed
# /setquality 480p|720p|1080p command with a proper inline-button menu,
# same shape as the reference encode bots' /settings panel: format, codec,
# CRF, preset, 10-bit, resolution, and audio codec/bitrate/channels.

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .. import ALL_CHATS, help_dict
from ..utils.db import get_settings, set_setting
from ..utils.compress import VALID_PRESETS, RESOLUTIONS, CODEC_ENCODERS, AUDIO_ENCODERS, AUDIO_CHANNELS, CONTAINER_EXT

CRF_CHOICES = (18, 20, 22, 24, 26, 28, 30, 32)
AUDIO_BITRATE_CHOICES = ('64k', '96k', '128k', '160k', '192k', '256k')

CB_PREFIX = 'enc:'


def _cb(field, value):
    return f'{CB_PREFIX}{field}:{value}'


def _row(options, field, current, cols=4):
    buttons = []
    for opt in options:
        label = f'• {opt} •' if str(opt) == str(current) else str(opt)
        buttons.append(InlineKeyboardButton(label, callback_data=_cb(field, opt)))
    return [buttons[i:i + cols] for i in range(0, len(buttons), cols)]


def _build_menu(s):
    rows = []
    rows.append([InlineKeyboardButton('── Container ──', callback_data='enc:noop:x')])
    rows += _row(CONTAINER_EXT.keys(), 'encode_format', s['encode_format'], cols=3)
    rows.append([InlineKeyboardButton('── Codec ──', callback_data='enc:noop:x')])
    rows += _row(CODEC_ENCODERS.keys(), 'encode_codec', s['encode_codec'], cols=2)
    rows.append([InlineKeyboardButton('── CRF (lower = better quality, bigger file) ──', callback_data='enc:noop:x')])
    rows += _row(CRF_CHOICES, 'encode_crf', s['encode_crf'], cols=4)
    rows.append([InlineKeyboardButton('── Preset ──', callback_data='enc:noop:x')])
    rows += _row(VALID_PRESETS, 'encode_preset', s['encode_preset'], cols=3)
    rows.append([InlineKeyboardButton(
        f"10-bit: {'ON' if s['encode_10bit'] else 'OFF'} (h265 only)",
        callback_data=_cb('encode_10bit', 'toggle')
    )])
    rows.append([InlineKeyboardButton('── Resolution ──', callback_data='enc:noop:x')])
    rows += _row(RESOLUTIONS.keys(), 'encode_resolution', s['encode_resolution'], cols=3)
    rows.append([InlineKeyboardButton('── Audio codec ──', callback_data='enc:noop:x')])
    rows += _row(AUDIO_ENCODERS.keys(), 'encode_audio_codec', s['encode_audio_codec'], cols=3)
    if s['encode_audio_codec'] != 'copy':
        rows.append([InlineKeyboardButton('── Audio bitrate ──', callback_data='enc:noop:x')])
        rows += _row(AUDIO_BITRATE_CHOICES, 'encode_audio_bitrate', s['encode_audio_bitrate'], cols=3)
        rows.append([InlineKeyboardButton('── Audio channels ──', callback_data='enc:noop:x')])
        rows += _row(AUDIO_CHANNELS.keys(), 'encode_audio_channels', s['encode_audio_channels'], cols=3)
    rows.append([InlineKeyboardButton('Close', callback_data='enc:close:x')])
    return InlineKeyboardMarkup(rows)


def _summary_text(s):
    return (
        '<b>Encode settings</b>\n'
        f"Container: <code>{s['encode_format']}</code> | Codec: <code>{s['encode_codec']}</code> | "
        f"10-bit: <code>{'on' if s['encode_10bit'] else 'off'}</code>\n"
        f"CRF: <code>{s['encode_crf']}</code> | Preset: <code>{s['encode_preset']}</code> | "
        f"Resolution: <code>{s['encode_resolution']}</code>\n"
        f"Audio: <code>{s['encode_audio_codec']}</code>"
        + (f" @ <code>{s['encode_audio_bitrate']}</code>, <code>{s['encode_audio_channels']}</code> ch" if s['encode_audio_codec'] != 'copy' else '')
        + '\n\nTap a value below to change it.'
    )


@Client.on_message(filters.command(['encsettings', 'encset']) & filters.chat(ALL_CHATS))
async def encode_settings_panel(client, message):
    s = await get_settings(message.from_user.id)
    await message.reply_text(_summary_text(s), reply_markup=_build_menu(s))


@Client.on_callback_query(filters.regex(r'^enc:'))
async def encode_settings_callback(client, callback_query):
    message = callback_query.message
    reply_to = message.reply_to_message
    owner_id = (reply_to.from_user.id if reply_to and reply_to.from_user else None) or callback_query.from_user.id
    if callback_query.from_user.id != owner_id:
        await callback_query.answer("This isn't your settings panel.", show_alert=True)
        return

    _, field, value = callback_query.data.split(':', 2)
    user_id = callback_query.from_user.id

    if field == 'noop':
        await callback_query.answer()
        return
    if field == 'close':
        await callback_query.answer()
        await message.delete()
        return

    if field == 'encode_10bit':
        current = (await get_settings(user_id))['encode_10bit']
        await set_setting(user_id, 'encode_10bit', not current)
    elif field == 'encode_crf':
        await set_setting(user_id, field, int(value))
    else:
        await set_setting(user_id, field, value)

    s = await get_settings(user_id)
    await callback_query.answer()
    await message.edit_text(_summary_text(s), reply_markup=_build_menu(s))


help_dict['encsettings'] = ('Encode Settings', '''
/encsettings - open the interactive encode-settings panel (container, codec, CRF, preset, 10-bit, resolution, audio)
/encset - alias for /encsettings
''')
