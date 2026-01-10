# handlers/ai_assistant.py
import os
import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

AI_API_URL = os.getenv("AI_API_URL", "https://futurenur.pythonanywhere.com/ai/chat")

# RiseUp uchun prompt
BASE_PROMPT = (
    "Sen RiseUp platformasining AI mentori-san.\n"
    "Har doim faqat o‘zbek tilida javob ber.\n"
    "Javoblaring qisqa, tushunarli va amaliy bo‘lsin (3-7 gap).\n"
    "Agar savol RiseUp kurslari (frontend/backend, dizayn, IT, hamda ingliz tilda) yoki o‘qish jarayoniga aloqador bo‘lmasa,"
    "muloyim rad et va RiseUp mavzusiga qaytar.\n"
    "Misol uchun, agar foydalanuvchi shaxsiy hayot, siyosat yoki boshqa mavzuda savol bersa, muloyimlik bilan rad et va RiseUp haqida gapir.\n"
    "Foydalanuvchiga yordam berish hamda uni progress qilishga undash uchun harakat qil.\n"
    "Seni yosh hamda iqtidorli RiseUp jamoasi yaratgan va doimo foydalanuvchilarga yordam berishga tayyorsan.\n"
    "RiseUp ning rasmiy veb-sayti: https://riseuply.vercel.app\n"
    "Foydalanuvchiga hissa qo'shishini so'rab, /hissa komandasi orqali yordam berishni tavsiya qil."
    "RiseUp ning Telegram kanali: https://t.me/riseuply\n"
)

async def call_ai(message_text: str) -> str:
    timeout = aiohttp.ClientTimeout(total=30)
    payload = {
        "message": message_text,
        "promt": f"{BASE_PROMPT}\nFoydalanuvchi savoli: {message_text}\nJavob ber:"
    }

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            # Avval POST (eng to'g'ri)
            async with session.post(AI_API_URL, json=payload) as resp:
                if resp.status != 200:
                    return f"⚠️ AI server xatosi: HTTP {resp.status}"
                data = await resp.json(content_type=None)
        except aiohttp.ClientError:
            # Fallback: agar server POST qabul qilmasa GET sinab ko'ramiz
            try:
                async with session.get(AI_API_URL, params=payload) as resp:
                    if resp.status != 200:
                        return f"⚠️ AI server xatosi: HTTP {resp.status}"
                    data = await resp.json(content_type=None)
            except Exception:
                return "⚠️ AI bilan ulanishda muammo bo‘ldi"
        except Exception:
            return "⚠️ AI javob bermadi (timeout yoki xato)"

    if data.get("status") == "success":
        return data.get("response", "Javob yo‘q")
    return "⚠️ AI javobida xatolik"

def chunk_text(text: str, size: int = 4000):
    for i in range(0, len(text), size):
        yield text[i:i+size]

# ✅ /ai komandasi: /ai savol...
@router.message(Command("ai"))
async def ai_command(message: Message):
    query = message.text.replace("/ai", "", 1).strip() if message.text else ""
    if not query:
        await message.answer("🧠 /ai dan keyin savolingizni yozing.\nMasalan: /ai Bugun kun qanday?")
        return

    await message.chat.do("typing")
    answer = await call_ai(query)

    for part in chunk_text(answer):
        await message.reply(part)

# ✅ Gruppada reply bo'lsa ham ishlaydi (xohlasangiz qoldiramiz)
@router.message(F.text)
async def ai_reply_mode(message: Message):
    # Gruppada: faqat botga reply bo‘lsa ishlasin
    if message.chat.type in ("group", "supergroup"):
        if not (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot):
            return
        query = (message.text or "").strip()
        if not query:
            return

        await message.chat.do("typing")
        answer = await call_ai(query)
        for part in chunk_text(answer):
            await message.reply(part)
