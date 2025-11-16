from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔁 Javob yozish", callback_data="reply_user"),
        InlineKeyboardButton("❌ O‘chirish", callback_data="delete_user")
    )
    return keyboard
