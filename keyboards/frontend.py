from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

front = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "HTML darslari"),
            KeyboardButton(text = "CSS darslari"),
            KeyboardButton(text = "JavaScript darslari")
        ],
        [
            KeyboardButton(text = "🔙 Ortga")
        ],
    ],
    resize_keyboard = True
)