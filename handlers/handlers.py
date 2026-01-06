from aiogram import Bot, types, Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import sign, TaskSolve
from keyboards.nomer import nomer
from keyboards.web import web
from keyboards.lang import inline_lang
from keyboards.uzbreply import uzbreply
from keyboards.rusreply import rusreply
from keyboards.engreply import engreply
from keyboards.frontend import front
from keyboards.rufront import rufront
from keyboards.engfront import engfront
from keyboards.hissa import hissa

import re
import os
import aiohttp
import asyncio
import time
from datetime import datetime

router = Router()

# ==================== API URL'LAR ====================

API_LOGIN = "https://api.riseuply.uz/api/auth/login/"
API_LINK_TG = "https://api.riseuply.uz/api/auth/link-telegram/"
API_TASKS = "https://api.riseuply.uz/api/tasks/"
API_TASK_DETAIL = "https://api.riseuply.uz/api/tasks/{id}/"


# telegram_id -> {"access": ..., "refresh": ..., "email": ..., "username": ...}
USER_TOKENS = {}

# ==================== GLOBAL AIOHTTP SESSION (LAG + UNCLOSED FIX) ====================

HTTP_SESSION: aiohttp.ClientSession | None = None


def set_api_base(url: str):
   
    global API_LOGIN, API_LINK_TG, API_TASKS, API_TASK_DETAIL
    url = url.rstrip("/")
    API_LOGIN = f"{url}/api/auth/login/"
    API_LINK_TG = f"{url}/api/auth/link-telegram/"
    API_TASKS = f"{url}/api/tasks/"
    API_TASK_DETAIL = f"{url}/api/tasks/{{id}}/"


async def init_http_session():
    """main.py startup'ida chaqirasiz."""
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        timeout = aiohttp.ClientTimeout(total=20, connect=10, sock_read=20)
        connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
        HTTP_SESSION = aiohttp.ClientSession(timeout=timeout, connector=connector)


async def close_http_session():
    """main.py shutdown'ida chaqirasiz."""
    global HTTP_SESSION
    if HTTP_SESSION and not HTTP_SESSION.closed:
        await HTTP_SESSION.close()
    HTTP_SESSION = None


async def api_request(method: str, url: str, *, access: str | None = None, json: dict | None = None):
    """
    Barcha API call shu orqali o'tsin.
    Unclosed connection bo'lmasligi uchun 'async with' ishlatadi.
    """
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        await init_http_session()

    headers = {}
    if access:
        headers["Authorization"] = f"Bearer {access}"

    async with HTTP_SESSION.request(method, url, json=json, headers=headers) as resp:
        # Connection reuse (keep-alive) uchun body o'qilishi muhim
        ctype = resp.headers.get("Content-Type", "")
        if "application/json" in ctype:
            data = await resp.json()
        else:
            data = await resp.text()

        return resp.status, data


# ==================== YORDAMCHI FUNKSIYALAR ====================

def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def format_datetime(dt_str: str) -> str:
    """
    DRF dan keladigan datetime stringni chiroyli formatga o'tkazish:
    2025-12-06T16:30:00Z  ->  06.12.2025 • 21:30
    """
    if not dt_str:
        return "—"
    try:
        s = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.strftime("%d.%m.%Y • %H:%M")
    except Exception:
        return dt_str


def normalize_text(s: str) -> str:
    """Taqqoslash uchun matnni normalize qilish (lower, bo'sh joylarni tozalash)."""
    return re.sub(r"\s+", " ", s).strip().lower()


async def evaluate_answer(task: dict, user_answer_raw: str) -> tuple[bool, str]:
    """
    Task va foydalanuvchi javobini qabul qilib,
    (correct, result_text) qaytaradi.
    """
    user_answer_raw = user_answer_raw.strip()
    user_answer_norm = normalize_text(user_answer_raw)

    result_text = ""
    correct = False

    # === SHORT ANSWER ===
    if task["type"] == "short":
        expected = (task.get("correct_short") or "").strip()
        expected_norm = normalize_text(expected)

        correct = bool(expected_norm) and (user_answer_norm == expected_norm)

        if correct:
            result_text = (
                "✅ *To‘g‘ri javob!*\n\n"
                f"📌 Sizning javobingiz: `{user_answer_raw}`\n"
                f"✅ To‘g‘ri javob: `{expected}`"
            )
        else:
            result_text = (
                "❌ *Noto‘g‘ri javob.*\n\n"
                f"📌 Sizning javobingiz: `{user_answer_raw}`\n"
                f"✅ To‘g‘ri javob: `{expected or '—'}`"
            )

    # === MCQ / CHECKBOX ===
    else:
        options = task.get("options", [])
        if not options:
            return False, "⚠️ Bu savol uchun variantlar topilmadi."

        # 1) Raqam ko‘rinishida javoblarni ajratib olamiz (1, 2, 3 ...)
        nums = re.findall(r"\d+", user_answer_raw)
        chosen_indexes = set()

        if nums:
            for n in nums:
                idx = int(n) - 1
                if 0 <= idx < len(options):
                    chosen_indexes.add(idx)

        # 2) Agar raqam topilmasa, matn bo‘yicha qidiramiz
        if not chosen_indexes:
            # checkbox bo'lsa bir nechta matn bo'lishi mumkin
            # "Backend, Frontend" -> ["backend", "frontend"]
            parts = re.split(r"[,\n;]+", user_answer_raw)
            parts = [normalize_text(p) for p in parts if p.strip()]

            for i, opt in enumerate(options):
                opt_norm = normalize_text(opt["text"])
                if opt_norm in parts or any(p in opt_norm for p in parts):
                    chosen_indexes.add(i)

            # agar mcq bo'lsa va hech nima topilmasa, to‘liq matn bo‘yicha ham solishtiramiz
            if not chosen_indexes and task["type"] == "mcq":
                for i, opt in enumerate(options):
                    if normalize_text(opt["text"]) == user_answer_norm:
                        chosen_indexes.add(i)
                        break

        correct_indexes = {i for i, o in enumerate(options) if o["correct"]}

        if task["type"] == "mcq":
            correct = len(chosen_indexes) == 1 and chosen_indexes == correct_indexes
        else:  # checkbox
            correct = chosen_indexes == correct_indexes and len(correct_indexes) > 0

        user_chosen_texts = ", ".join(
            options[i]["text"] for i in sorted(chosen_indexes)
        ) if chosen_indexes else "—"

        correct_texts = ", ".join(
            o["text"] for o in options if o["correct"]
        ) or "—"

        if correct:
            result_text = (
                "✅ *To‘g‘ri javob!*\n\n"
                f"📌 Siz tanlagan variant(lar): {user_chosen_texts}\n"
                f"✅ To‘g‘ri variant(lar): {correct_texts}"
            )
        else:
            result_text = (
                "❌ *Noto‘g‘ri javob.*\n\n"
                f"📌 Siz tanlagan variant(lar): {user_chosen_texts}\n"
                f"✅ To‘g‘ri variant(lar): {correct_texts}"
            )

    return correct, result_text


# ==================== AUTH / START BLOKI ====================

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    tg_id = message.from_user.id

    # 🔍 Agar avval login qilgan bo'lsa (USER_TOKENS ichida bo'lsa)
    existing = USER_TOKENS.get(tg_id)
    if existing:
        # Har ehtimolga qarshi state ni tozalaymiz
        await state.clear()

        username = existing.get("username") or message.from_user.full_name or "foydalanuvchi"
        await message.answer(
            f"Assalomu alaykum, {username}! 👋\n\n"
            "Siz allaqachon akkauntingizni botga bog‘lab bo‘lgansiz ✅\n\n"
            "Quyidagi buyruqlardan foydalanishingiz mumkin:\n"
            "📌 /task — sayt orqali yaratilgan savollaringiz ro'yxati\n"
            "📌 /course — kurslar menyusi\n"
            "📌 /help — qo'llanma\n"
            "💰 /hissa — RiseUp ga hissa qo'shing\n\n"
            "Yangi savollar yaratish uchun yoki natijangizni bilish uchun riseuply.uz saytiga kiring 😉"
        )
        return

    # 🆕 Agar birinchi marta kelayotgan bo'lsa, login jarayonini boshlaymiz
    await state.set_state(sign.login)
    await message.answer(
        "Assalomu alaykum! 👋\n"
        "Iltimos, riseuply.uz website dagi emailingizni kiriting:"
    )


@router.message(sign.login)
async def get_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(sign.password)
    await message.answer("Endi parolingizni kiriting:")


@router.message(sign.password)
async def get_password(message: Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    data = await state.get_data()

    email = data["login"]
    password = data["password"]

    # 1) LOGIN
    status, tokens = await api_request("POST", API_LOGIN, json={
        "email": email,
        "password": password
    })

    if status != 200:
        await message.answer("❌ Email yoki parol noto‘g‘ri!\n/start bilan qaytadan urinib ko‘ring.")
        await state.clear()
        return

    access = tokens["access"]
    username = tokens.get("username") or "foydalanuvchi"

    # 2) TELEGRAM ID NI BOG‘LAYMIZ
    tg_id = message.from_user.id
    await api_request(
        "POST",
        API_LINK_TG,
        access=access,
        json={"telegram_id": tg_id}
    )

    # 2.1) TOKENLARNI XOTIRAGA SAQLAYMIZ
    USER_TOKENS[tg_id] = {
        "access": tokens["access"],
        "refresh": tokens.get("refresh"),
        "email": email,
        "username": username,
        "saved_at": time.time(),
    }

    # 3) Foydalanuvchiga salom
    await message.answer(
        f"✅ Akkauntingiz botga muvaffaqiyatli bog‘landi!\n"
        f"Xush kelibsiz, {username.title()}! 🎉\n\n"
        f"📌/task — sayt orqali yaratilgan savollaringiz ro'yxati\n"
        f"📌/course — kurslar menyusi\n"
        f"📌/ai - RiseUp AI yordamchi\n"
        f"📌/help — qo'llanma\n"
        f"💰 /hissa — RiseUp ga hissa qo'shing"
        f"\n\nYangi savollar yaratish uchun yoki natijangizni bilish uchun riseuply.uz saytiga kiring 😉"
    )
    await state.clear()


# ==================== TASKLAR BILAN ISHLASH (INTERAKTIV) ====================

@router.message(Command("task"))
async def show_tasks(message: Message, state: FSMContext):
    """
    /task -> backend'dan aynan shu foydalanuvchining tasklarini olib keladi
    va inline tugmalar bilan chiqaradi.
    """
    await state.clear()

    tg_id = message.from_user.id
    tokens = USER_TOKENS.get(tg_id)

    if not tokens:
        await message.answer(
            "⛔ Avval akkauntingizni botga bog'lab oling.\n\n"
            "Buning uchun:\n"
            "1) /start buyrug'ini bosing\n"
            "2) Email va parolni kiriting\n"
            "3) Shundan keyin /task buyrug'i ishlaydi ✅"
        )
        return

    access = tokens["access"]

    status, tasks = await api_request("GET", API_TASKS, access=access)

    if status == 401:
        await message.answer(
            "⛔ Sessiyangiz tugagan ko'rinadi.\n"
            "Iltimos, /start orqali qaytadan login qiling."
        )
        return

    if status != 200:
        await message.answer("⚠️ Tasklarni olishda xatolik yuz berdi. Keyinroq qayta urinib ko‘ring.")
        return

    if not tasks:
        await message.answer("📭 Sizda hozircha birorta ham task yo'q.\n riseuply.uz saytidan kirib hoziroq boshlang!")
        return

    kb = InlineKeyboardBuilder()
    for t in tasks[:10]:
        title = t["title"]
        short_title = title if len(title) <= 20 else title[:17] + "..."
        kb.button(
            text=f"#{t['id']} • {short_title}",
            callback_data=f"task_{t['id']}"
        )
    kb.adjust(1)

    await message.answer(
        f"📚 Sizda jami {len(tasks)} ta savollar mavjud.\n\n"
        f"Ko‘rmoqchi bo‘lgan savolingizni tanlang:",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data.startswith("task_"))
async def show_task_detail(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    tokens = USER_TOKENS.get(tg_id)

    if not tokens:
        await callback.message.answer("⛔ Avval /start orqali akkauntni bog'lab oling.")
        await callback.answer()
        return

    access = tokens["access"]
    task_id = int(callback.data.split("_")[1])

    status, task = await api_request("GET", API_TASK_DETAIL.format(id=task_id), access=access)

    if status != 200:
        await callback.message.answer("⚠️ Bu taskni olishda xatolik yuz berdi.")
        await callback.answer()
        return

    type_map = {
        "short": "Qisqa javob",
        "mcq": "Ko‘p tanlov",
        "checkbox": "Checkbox"
    }

    lines = []
    lines.append(f"🆔 Task #{task['id']}")
    lines.append(f"❓ Savol: {task['title']}")
    lines.append(f"🔁 Turi: {type_map.get(task['type'], task['type'])}")

    if task.get("category"):
        lines.append(f"🏷 Kategoriya: {task['category']}")

    if task.get("scheduled_time"):
        nice_dt = format_datetime(task["scheduled_time"])
        lines.append(f"⏰ Rejalashtirilgan: {nice_dt}")

    lines.append("")

    if task["type"] == "short":
        lines.append("✍️ Bu savol qisqa javob talab qiladi.")
        lines.append("Javobingizni matn ko‘rinishida yozib yuboring (masalan: Backend).")
    else:
        lines.append("📌 Variantlar:")
        for idx, opt in enumerate(task.get("options", []), start=1):
            lines.append(f"{idx}) {opt['text']}")

        if task["type"] == "mcq":
            lines.append("\nℹ️ Faqat bitta to‘g‘ri javob bor.")
            lines.append("Javobni matn ko‘rinishida ham, raqam ko‘rinishida ham yozishingiz mumkin (masalan: `1` yoki `Backend`).")
        elif task["type"] == "checkbox":
            lines.append("\nℹ️ Bir nechta to‘g‘ri javob bo‘lishi mumkin.")
            lines.append("Masalan: `1 3` yoki `Backend, Frontend` ko‘rinishida.")

    lines.append(
        "\n✅ Endi javobingizni shu chatga yozib yuboring.\n"
        "❌ Bekor qilish uchun /cancel buyrug'idan foydalanishingiz mumkin."
    )

    await callback.message.edit_text("\n".join(lines))

    await state.set_state(TaskSolve.waiting_answer)
    await state.update_data(task_id=task_id)
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_answer(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Javob berish bekor qilindi. Istasangiz /task bilan qayta tanlashingiz mumkin.")


@router.message(TaskSolve.waiting_answer)
async def check_task_answer(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    tokens = USER_TOKENS.get(tg_id)

    if not tokens:
        await message.answer("⛔ Sessiya topilmadi. /start orqali qayta kirib ko‘ring.")
        await state.clear()
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    if not task_id:
        await message.answer("⚠️ Task ma'lumoti topilmadi. /task buyrug'i bilan qayta urinib ko‘ring.")
        await state.clear()
        return

    access = tokens["access"]

    status, task = await api_request("GET", API_TASK_DETAIL.format(id=task_id), access=access)

    if status != 200:
        await message.answer("⚠️ Taskni olishda xatolik yuz berdi.")
        await state.clear()
        return

    correct, result_text = await evaluate_answer(task, message.text or "")
    await message.answer(result_text, parse_mode="Markdown")
    
    async with aiohttp.ClientSession() as session:
        await session.post(
            "https://api.riseuply.uz/api/stats/update/",
            json={"correct": correct},
            headers={"Authorization": f"Bearer {tokens['access']}"}
        )
        
    await state.clear()
    await message.answer("🔁 Yana savol ko‘rmoqchi bo‘lsangiz, /task buyrug‘ini yuboring.")


@router.message(F.reply_to_message & F.text & ~F.text.startswith("/"))
async def reply_task_answer(message: Message):
    tg_id = message.from_user.id
    tokens = USER_TOKENS.get(tg_id)
    if not tokens:
        return

    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    m = re.search(r"Task #(\d+)", replied.text)
    if not m:
        return

    task_id = int(m.group(1))

    status, task = await api_request("GET", API_TASK_DETAIL.format(id=task_id), access=tokens["access"])

    if status != 200:
        await message.answer("⚠️ Savolni olishda xatolik yuz berdi.")
        return

    correct, result_text = await evaluate_answer(task, message.text or "")
    await message.answer(result_text, parse_mode="Markdown")

    async with aiohttp.ClientSession() as session:
        await session.post(
            "https://api.riseuply.uz/api/stats/update/",
            json={"correct": correct},
            headers={"Authorization": f"Bearer {tokens['access']}"}
        )

# ==================== KURS MENYU ====================

@router.message(Command("course"))
async def start_menu(message: Message):
    await message.answer("Maroqli o'rganing😉", reply_markup=web)


# ==================== Kurslar menyusi ====================

@router.message(F.text == "Backend")
async def backen(message: Message):
    await message.answer("Kerakli tilni tanlang: ", reply_markup=inline_lang())


@router.callback_query(F.data.startswith("lang_"))
async def backend_lang_callback(callback: CallbackQuery):
    code = callback.data.split("_")[1]  # "uzb", "ru", "eng", "back"

    if code == "uzb":
        await callback.message.answer("Siz o'zbek tilini tanladingiz", reply_markup=uzbreply)
    elif code == "ru":
        await callback.message.answer("Вы выбрали русский язык", reply_markup=rusreply)
    elif code == "eng":
        await callback.message.answer("You choose English", reply_markup=engreply)
    elif code == "back":
        await callback.message.answer("Ortga", reply_markup=web)

    await callback.message.edit_reply_markup()
    await callback.answer()


@router.message(F.text == "🔙 Ortga")
async def ortg(message: Message):
    await message.answer("Ortga", reply_markup=web)


@router.message(F.text == "Python asoslari")
async def pyth(message: Message):
    await message.answer(
        "Python darslarini 0 dan boshlab o'rganing:\n\n"
        "https://www.youtube.com/watch?v=ZqFjXM8k-PY&list=PLwsopmzfbOn9Lw5D7a26THpBDgAma1Sus"
    )


@router.message(F.text == "Django darslari")
async def django_uz(message: Message):
    await message.answer(
        "Django darslarini professional tarzda o'rganing 0dan o'zingizni website qilishingizgacha:\n\n"
        "https://www.youtube.com/watch?v=49_C_3kkW6g&list=PLWoHEZ4vq7z5TR9I-TYLnqN0vgdHHrOmS"
    )


@router.message(F.text == "Django Rest Framework darslari")
async def drf_uz(message: Message):
    await message.answer(
        "Django rest framework darslarini hamda api larni mukammal urganing:\n\n"
        "https://www.youtube.com/watch?v=o7SVadHcXjM&list=PLm-TVk1aJmO4gKl0EuQei16B6Wi4tRhP8"
    )


@router.message(F.text == "Aiogram darslari")
async def aiogram_uz(message: Message):
    await message.answer(
        "Aiogramda 0dan toki o'zingizni botingizni qilib chiqishgacha:\n\n"
        "https://www.youtube.com/watch?v=FC2ztmTq10w&list=PLyABYrL3eBgWnQ_qUylmhChB1J6t4B38R"
    )


@router.message(F.text == "Python Уроки")
async def ur(message: Message):
    await message.answer(
        "Python с нуля:\n\n"
        "https://www.youtube.com/watch?v=34Rp6KVGIEM&list=PLDyJYA6aTY1lPWXBPk0gw6gR8fEtPDGKa"
    )


@router.message(F.text == "Django Уроки")
async def djang(message: Message):
    await message.answer(
        "Профессионально изучите уроки Django с нуля до создания собственного сайта:\n\n"
        "https://www.youtube.com/watch?v=L-FyeHQwo4U&list=PLDyJYA6aTY1nZ9fSGcsK4wqeu-xaJksQQ"
    )


@router.message(F.text == "Django Rest Framework Уроки")
async def drf_ru(message: Message):
    await message.answer(
        "Изучите руководства и API фреймворка Django REST:\n\n"
        "https://www.youtube.com/watch?v=i-uvtDKeFgE&list=PLA0M1Bcd0w8xZA3Kl1fYmOH_MfLpiYMRs"
    )


@router.message(F.text == "Aiogram Уроки")
async def aiogra(message: Message):
    await message.answer(
        "С нуля до создания собственного бота на Aiogram:\n\n"
        "https://www.youtube.com/watch?v=i07-M7m13bM&list=PLV0FNhq3XMOJ31X9eBWLIZJ4OVjBwb-KM"
    )


@router.message(F.text == "🔙 Назад")
async def nazad(message: Message):
    await message.answer("Назад", reply_markup=web)


@router.message(F.text == "Python for beginners")
async def begin(message: Message):
    await message.answer(
        "Python for beginners:\n\n"
        "https://www.youtube.com/watch?v=K5KVEU3aaeQ"
    )


@router.message(F.text == "Django lessons")
async def less(message: Message):
    await message.answer(
        "Django lessons from scratch to own website:\n\n"
        "https://www.youtube.com/watch?v=rHux0gMZ3Eg"
    )


@router.message(F.text == "Django Rest Framework lessons")
async def django_en(message: Message):
    await message.answer(
        "DRF lessons for beginners with API:\n\n"
        "https://www.youtube.com/watch?v=c708Nf0cHrs"
    )


@router.message(F.text == "Aiogram lessons")
async def aiogram_en(message: Message):
    await message.answer(
        "Create your own telegram bot with aiogram library in python:\n\n"
        "https://www.youtube.com/watch?v=rDG09TlYSwo&list=PLt2KnIqdk1FEm4lmGuxxz9OjiX7HLnYEa"
    )


@router.message(F.text == "🔙 Back")
async def back(message: Message):
    await message.answer("Back", reply_markup=web)


# ==================== FRONTEND BLOKI ====================

@router.message(F.text == "Frontend")
async def frontd(message: Message):
    await message.answer("Kerakli tilni tanlang: ", reply_markup=inline_front())


def inline_front():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 Uzb", callback_data="til_ozb")
    builder.button(text="🇷🇺 Ru", callback_data="til_rus")
    builder.button(text="🇺🇸 Eng", callback_data="til_en")
    builder.button(text="🔙 Ortga", callback_data="til_backd")
    builder.adjust(3, 1)
    return builder.as_markup()


@router.callback_query(F.data.startswith("til_"))
async def frontend_lang_callback(callback: CallbackQuery):
    code = callback.data.split("_")[1]  # "ozb", "rus", "en", "backd"

    if code == "ozb":
        await callback.message.answer("Siz o'zbek tilini tanladingiz", reply_markup=front)
    elif code == "rus":
        await callback.message.answer("Вы выбрали русский язык", reply_markup=rufront)
    elif code == "en":
        await callback.message.answer("You chose English", reply_markup=engfront)
    elif code == "backd":
        await callback.message.answer("Ortga", reply_markup=web)

    await callback.message.edit_reply_markup()
    await callback.answer()


@router.message(F.text == "HTML darslari")
async def uzhtml(message: Message):
    await message.answer(
        "HTML darslarini 0dan o'rganing:\n\n"
        "https://www.youtube.com/watch?v=9dUhZq9dkHM&list=PLpDyZ4xZcDg_aAzP6pDD1PRsYCSdheveS"
    )


@router.message(F.text == "CSS darslari")
async def uzcss(message: Message):
    await message.answer(
        "CSS darslarini hamda stylelarni mukammal o'rganish:\n\n"
        "https://www.youtube.com/watch?v=KPPhQ0F-SDY&list=PLpDyZ4xZcDg_gyII__1jtnE2FEgqpfJU8"
    )


@router.message(F.text == "JavaScript darslari")
async def uzjava(message: Message):
    await message.answer(
        "JavaScript dasrlarini hamda sayt qilishni mukammal o'rganish:\n\n"
        "https://www.youtube.com/watch?v=q8yclECd9CY&list=PLpDyZ4xZcDg8fRiY6xgsQcDiMjNYJhNjE"
    )


@router.message(F.text == "HTML Уроки")
async def htmlru(message: Message):
    await message.answer(
        "Изучите уроки HTML с нуля:\n\n"
        "https://www.youtube.com/watch?v=_R5a-Kc0pRc&list=PLDyJYA6aTY1nlkG0gBj96XDmDSC4Fy1TO"
    )


@router.message(F.text == "CSS Уроки")
async def cssru(message: Message):
    await message.answer(
        "Изучите уроки и стили CSS:\n\n"
        "https://www.youtube.com/watch?v=hft4XYApT44&list=PLDyJYA6aTY1meZ3d08sRILB46OJ-wojF2"
    )


@router.message(F.text == "JavaScript Уроки")
async def javaru(message: Message):
    await message.answer(
        "Подробно изучите учебные пособия по JavaScript и создание веб-сайтов:\n\n"
        "https://www.youtube.com/watch?v=fHl7UyRjOf0&list=PLDyJYA6aTY1kJIwbYHzGOuvSMNTfqksmk"
    )


@router.message(F.text == "HTML for beginners")
async def htmleng(message: Message):
    await message.answer(
        "Learn HTML from zero:\n\n"
        "https://www.youtube.com/watch?v=HD13eq_Pmp8"
    )


@router.message(F.text == "CSS for beginners")
async def csseng(message: Message):
    await message.answer(
        "Learn CSS as well style:\n\n"
        "https://www.youtube.com/watch?v=wRNinF7YQqQ"
    )


@router.message(F.text == "JavaScript for beginners")
async def javaeng(message: Message):
    await message.answer(
        "Deep learning JavaScript and learn create website:\n\n"
        "https://www.youtube.com/watch?v=EerdGm-ehJQ"
    )


@router.message(Command("hissa"))
async def hissa_command(message: Message):
    user_id = message.from_user.id
    await message.answer(
        f"Salom, hurmatli foydalanuvchi! Sizning RiseUp botimizni rivojlantirishga bo'lgan qiziqishingiz uchun tashakkur! "
        f"Agar siz botimizga hissa qo'shishni xohlasangiz, quyidagi havola orqali buni amalga oshirishingiz mumkin."
        f"Sizning qo'llab-quvvatlashingiz biz uchun juda muhim va biz bunga juda minnatdormiz! "
        f"Sizning hissangiz riseuply.uz & @riseupuz_bot loyihamizni yanada yaxshilashga yordam beradi. Rahmat! 👇"
    , reply_markup=hissa)