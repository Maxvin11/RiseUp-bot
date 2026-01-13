from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

rufront = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "HTML Уроки"),
            KeyboardButton(text = "CSS Уроки"),
            KeyboardButton(text = "JavaScript Уроки")
        ],
        [
            KeyboardButton(text = "🔙 Назад")
        ]
    ],
    resize_keyboard = True
)