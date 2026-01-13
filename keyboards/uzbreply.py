from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

uzbreply = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "Python asoslari"),
            KeyboardButton(text = "Django darslari"),
            KeyboardButton(text = "Django Rest Framework darslari"),
            KeyboardButton(text = "Aiogram darslari"),
        ],
        [
            KeyboardButton(text = "🔙 Ortga")
        ]
    ],
    resize_keyboard = True
)