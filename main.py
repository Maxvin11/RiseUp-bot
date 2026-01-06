from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
import asyncio
import logging
from aiogram.filters import Command
from aiogram.types import Message, BotCommand

from handlers.handlers import router
from handlers.ai_assistant import router as ai_router
from aiogram.exceptions import TelegramNetworkError

# ✅ shu ikki importni qo‘shing:
from handlers.handlers import init_http_session, close_http_session

from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN topilmadi. .env yoki Railway Variables ni tekshiring.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


@dp.message(Command("help"))
async def helper(message: Message):
    await message.answer(
        """👋 RiseUp’ga xush kelibsiz!

Agar siz IT sohasida rivojlanishni, real skill olishni va
kelajagingizga sarmoya qilishni xohlasangiz —  
RiseUp aynan siz uchun yaratilgan platforma 🚀

RiseUpda siz:
- faqat nazariya emas,
- balki amaliy tajriba,
- va real topshiriqlar orqali o‘rganasiz 💪

---

🔧 RiseUp’da nimalarni o‘rganasiz?

📌 Backend yo‘nalishi
- Python asoslari  
- Django va Django Rest Framework (DRF)  
- API bilan ishlash  
- Backend mantiqi (real loyihalar asosida)

📌 Frontend boshlang‘ich
- HTML  
- CSS  
- JavaScript  
- Sayt tuzilishi va dizayn asoslari

📌 Amaliy mashqlar
- Har bir mavzudan keyin task
- Bilimingizni darhol sinab ko‘rasiz

---

🧠 Tasklar bilan ishlash (asosiy qism)

RiseUp’da asosiy urg‘u — amaliyotga 💯

Saytda yaratilgan savollarni Telegram bot orqali ishlaysiz:

- /task — sizga berilgan savollar ro‘yxati
- Savolni tanlaysiz
- Javob berasiz
- Natijani darhol bilasiz ✅
- Har bir savol bo‘yicha izohlar va to‘g‘ri javoblar bilan tanishasiz
- O'z natijangizni websayt orqali ham kuzatib borasiz

👉 Xatolardan qo‘rqmang — aynan shunday o‘sasiz 😉

---

🤖 RiseUp AI — shaxsiy yordamchingiz

Biror joy tushunarsiz bo‘ldimi? Muammo emas 😊

RiseUp AI sizga yordam beradi:

- Murakkab mavzularni sodda qilib tushuntiradi
- Kodlarni izohlaydi
- Tarjima qiladi
- Ingliz tilini o‘rganishda yordam beradi
- IT yo‘nalishlar bo‘yicha maslahat beradi

📌 /ai — AI’ga savol berish  
(Hozircha oddiy yordamchi, keyinchalik yanada kuchli bo‘ladi 🔥)

---

🎯 Qanday boshlash kerak?

Boshlash juda oson:

1. /start — akkauntingizni botga bog‘lang
2. /course — yo‘nalishni tanlang
3. O‘rganing va mashq qiling
4. /task — bilimni tekshiring
5. /ai — tushunmagan joyingizni so‘rang

---

🚀 RiseUp — bu shunchaki kurs emas

Bu:
- o‘zingizni rivojlantirish muhiti
- intizom
- va har kuni 1 qadam oldinga yurish

💙 O‘rganing • Amaliyot qiling • O‘sib boring  
RiseUp bilan kelajagingizni bugundan boshlang!
"""
    )


async def main():
    logging.basicConfig(level=logging.INFO)

    dp.include_router(router)
    dp.include_router(ai_router)
    try:
        await bot.set_my_commands([
        BotCommand(command="/start", description="Botni ishga tushirish"),
        BotCommand(command="/help", description="Yordam"),
        BotCommand(command="/course", description="Kurslar ro'yxati"),
        BotCommand(command="/task", description="Vazifalar ro'yxati"),
        BotCommand(command="/ai", description="RiseUp AI-yordamchi"),
        BotCommand(command='/hissa', description="RiseUpga hissa qo'shish"),
    ], request_timeout=60)
    except TelegramNetworkError as e:
        print(f"⚠️ set_my_commands timeout, davom etamiz: {e}")
        # ✅ Startup
    await init_http_session()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        # ✅ Shutdown
        await close_http_session()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
