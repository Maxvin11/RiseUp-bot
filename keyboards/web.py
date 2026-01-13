from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

web = ReplyKeyboardMarkup(
    keyboard = [
    [
        KeyboardButton(text = "Backend"),
        KeyboardButton(text = "Frontend"),
        KeyboardButton(text = "Hissa qo'shish 💰", url = "https://t.me/timurbek_ustozai")
    ],
    
],
    resize_keyboard=True,
    one_time_keyboard = True
)