from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def inline_lang():
    builder = InlineKeyboardBuilder()
    builder.button(text = "🇺🇿 O'zbekcha", callback_data = "lang_uzb")
    builder.button(text = "🇷🇺 Ruscha", callback_data = "lang_ru")
    builder.button(text = "🇺🇸 Inglizcha", callback_data = "lang_eng")

    builder.button(text = "🔙 Ortga", callback_data = "lang_back")
    
    builder.adjust(3, 1)
    
    return builder.as_markup()