from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

rusreply = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "Python Уроки"),
            KeyboardButton(text = "Django Уроки"),
            KeyboardButton(text = "Django Rest Framework Уроки"),
            KeyboardButton(text = "Aiogram Уроки")
        ],
        [
            KeyboardButton(text = "🔙 Назад")
        ]
    ],
    resize_keyboard = True
)