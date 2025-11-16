from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Clientlar")],
        [KeyboardButton(text="❌ Clientni o'chirish")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)
