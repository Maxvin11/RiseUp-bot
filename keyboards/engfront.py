from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

engfront = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text = "HTML for beginners"),
            KeyboardButton(text = "CSS for beginners"),
            KeyboardButton(text = "JavaScript for beginners")
        ],
        [
            KeyboardButton(text = "🔙 Back")
        ],
    ],
    resize_keyboard = True
)