from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

engreply = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "Python for beginners"),
            KeyboardButton(text = "Django lessons"),
            KeyboardButton(text = "Django Rest Framework lessons"),
            KeyboardButton(text = "Aiogram lessons")
        ],
        [
            KeyboardButton(text = "🔙 Back")
        ]
    ],
    resize_keyboard = True
)