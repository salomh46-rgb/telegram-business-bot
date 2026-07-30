"""
=====================================================================
 JAVOHIRBEK ASQAROV — AI JAVOB BERUVCHI TELEGRAM BUSINESS BOT
                         (24/7 | Render.com Free Tier)
---------------------------------------------------------------------
 "Harness Engineering" qatlamlari:
   [1] BUSINESS LOGIC : aiogram 3.x  -> @dp.business_message() handler
   [2] AI LAYER       : openai SDK (AsyncOpenAI) + Gemini/OpenAI
                        OpenAI-mos endpoint — provayder env orqali almashadi
   [3] INFRASTRUCTURE : aiohttp web  -> Render Port binding + /health
   [4] ENV & SAFETY   : os.getenv()  -> maxfiy kalitlar koddan tashqarida
   [5] OBSERVABILITY  : logging + try/except + flood-himoya + fallback
=====================================================================
"""

import asyncio
import logging
import os
import time
from collections import deque
from typing import Deque, Dict

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BusinessConnection, Message

from dotenv import load_dotenv
from openai import AsyncOpenAI

# ----------------------------------------------------------------------
# 1. SOZLAMALAR (Environment Variables)
# ----------------------------------------------------------------------
load_dotenv()  # Lokal ishga tushirishda .env dan o'qiydi

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Render.com -> Environment Variables yoki "
        "lokal .env faylida sozlang."
    )

# --- AI qatlam (standart: Google Gemini BEPUL tarif) ---
# Kalit: https://aistudio.google.com/apikey dan bepul olinadi.
# OpenAI'ga o'tish uchun: AI_BASE_URL=https://api.openai.com/v1, AI_MODEL=gpt-4o-mini
AI_API_KEY: str = os.getenv("AI_API_KEY", "")
if not AI_API_KEY:
    raise RuntimeError(
        "AI_API_KEY topilmadi! Gemini kalitini https://aistudio.google.com/apikey "
        "dan oling va Environment Variables'ga qo'ying."
    )

AI_BASE_URL: str = os.getenv(
    "AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
AI_MODEL: str = os.getenv("AI_MODEL", "gemini-3.6-flash")
AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))

# --- Xotira va himoya ---
HISTORY_MAX_MESSAGES: int = int(os.getenv("HISTORY_MAX_MESSAGES", "12"))   # har suhbat uchun
FLOOD_LIMIT_MESSAGES: int = int(os.getenv("FLOOD_LIMIT_MESSAGES", "5"))    # oyna ichida max
FLOOD_LIMIT_SECONDS: int = int(os.getenv("FLOOD_LIMIT_SECONDS", "60"))     # oyna davomiyligi
USER_MESSAGE_MAX_CHARS: int = int(os.getenv("USER_MESSAGE_MAX_CHARS", "2000"))
TELEGRAM_MAX_CHARS: int = 4000  # Telegram limiti 4096 — chegarada yubormaymiz

HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))  # Render PORT ni avtomatik beradi

# ----------------------------------------------------------------------
# 2. SYSTEM PROMPT — Javohirbek haqidagi bilim bazasi
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
Siz Javohirbek Asqarovning shaxsiy AI-assistentisiz.
Vazifangiz — ish beruvchilar, HR mutaxassislar va mijozlar bergan savollarga
Javohirbekning rezyumesi va tajribasi asosida javob berish.

JAVOHIRBEK HAQIDA MA'LUMOTLAR:
- F.I.SH: Asqarov Javohir Iqboljon o'g'li (23 yosh, Toshkent)
- Kasbi: Middle Full-Stack Engineer / AI Integrator
- Telefon / Telegram: +998 (90) 508-33-02 | @Dr_eviluz
- Email: salomh46@gmail.com
- Ko'nikmalar: Python, FastAPI, React/Next.js, Node.js, PostgreSQL,
  OpenAI API, Gemini API, n8n, RAG, LangChain
- Tajriba: TechCorp Innovatsiya Markazi (Middle Full-Stack),
  SoftSolutions IT Kompaniyasi
- Loyihalar: Health AI System, Marketing Materials Generator,
  API Explorer, Telegram Business Bot (@Mabegerbot)

QAT'IY QOIDALAR:
1. Muloqotda doimo xushmuomala, professional va do'stona bo'ling.
2. Savollarga faqat Javohirbekning real tajribasiga tayanib javob bering.
   Bilmasangiz — uydirmang, @Dr_eviluz ga yo'naltiring.
3. Uchrashuv yoki suhbat haqida so'ralsa — Telegram @Dr_eviluz ga
   bog'lanishni taklif qiling.
4. Javobni DOIMO savol berilgan tilda bering (uz / ru / en).
5. Javoblar qisqa va lo'nda bo'lsin (ko'pi bilan 150 so'z).
   Telegram uchun oddiy matn yozing, HTML ishlatmang.
""".strip()

# AI xatolik berganda foydalanuvchini yo'qotmaslik uchun zaxira javob
AI_FALLBACK_TEXT = (
    "🙏 Kechirasiz, hozir texnik sabablarga ko'ra javob bera olmayapman.\n"
    "Iltimos, Javohirbekning o'ziga yozing: @Dr_eviluz"
)

# Faqat matnli xabarlarga xizmat ko'rsatish haqida javob
NON_TEXT_REPLY = (
    "👋 Xabaringiz uchun rahmat! Men Javohirbekning yordamchisiman va "
    "hozircha faqat matnli savollarga javob bera olaman.\n"
    "Murakkab savollar uchun: @Dr_eviluz"
)

# ----------------------------------------------------------------------
# 3. LOGGING
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("javohirbek-ai-bot")

# ----------------------------------------------------------------------
# 4. BOT, DISPATCHER, AI-CLIENT
# ----------------------------------------------------------------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Bitta universal klient: Gemini yoki OpenAI — faqat env orqali farq qiladi
ai_client = AsyncOpenAI(
    api_key=AI_API_KEY,
    base_url=AI_BASE_URL,
    timeout=AI_TIMEOUT_SECONDS,
)

# In-memory suhbat xotirasi: user_id -> oxirgi N ta xabar
chat_histories: Dict[int, Deque[dict]] = {}
# Flood oynasi: user_id -> so'rovlar vaqt tamg'alari
flood_windows: Dict[int, Deque[float]] = {}

STARTED_AT = time.time()


# ----------------------------------------------------------------------
# 5. AI QATLAM (yordamchi funksiyalar)
# ----------------------------------------------------------------------
def flood_check(user_id: int) -> bool:
    """Sliding-window himoya: API kvotani spamdan saqlaydi."""
    window = flood_windows.setdefault(user_id, deque())
    now = time.time()
    while window and now - window[0] > FLOOD_LIMIT_SECONDS:
        window.popleft()
    if len(window) >= FLOOD_LIMIT_MESSAGES:
        return False
    window.append(now)
    return True


async def generate_ai_reply(user_id: int, user_text: str) -> str:
    """Suhbat tarixini hisobga olgan holda AI javobini generatsiya qiladi."""
    history = chat_histories.setdefault(user_id, deque(maxlen=HISTORY_MAX_MESSAGES))

    payload = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_text},
    ]

    started = time.time()
    response = await ai_client.chat.completions.create(
        model=AI_MODEL,
        messages=payload,
        temperature=0.7,
        # Eslatma: max_tokens ayran OpenAI-mos endpointlarda qo'llanilmaydi
        # (Gemini'da ham, OpenAI'da ham param qabul qilish farq qiladi),
        # shuning uchun uzunlikni SYSTEM_PROMPT orqali cheklaymiz.
    )
    elapsed_ms = int((time.time() - started) * 1000)

    reply = (response.choices[0].message.content or "").strip()
    logger.info(
        "AI javob: model=%s | %d ms | user_id=%s | %d belgilik javob",
        AI_MODEL, elapsed_ms, user_id, len(reply),
    )

    if reply:
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
    return reply


def cleanup_memory() -> None:
    """In-memory saqlash cheksiz o'sib ketmasligi uchun davriy tozalash."""
    if len(chat_histories) > 5000:
        removed = len(chat_histories)
        chat_histories.clear()
        flood_windows.clear()
        logger.warning("Xotira tozalandi: %d ta suhbat tarixi o'chirildi", removed)


# ----------------------------------------------------------------------
# 6. TELEGRAM HANDLERLAR
# ----------------------------------------------------------------------
@dp.business_connection()
async def on_business_connection(connection: BusinessConnection) -> None:
    """Bot-Biznes ulanish holatini kuzatish (Logging)."""
    state = "✅ UZANDI" if connection.is_enabled else "⛔ O'CHIRILDI"
    logger.info(
        "Business connection: %s | user_id=%s | can_reply=%s",
        state, connection.user.id, connection.can_reply,
    )


@dp.business_message()
async def handle_business_message(message: Message) -> None:
    """Telegram Business shaxsiy xabarlariga Javohirbek nomidan AI javob."""
    sender = message.from_user

    # 1) Infinite loop himoyasi
    if sender is None or sender.is_bot:
        return

    conn_id = message.business_connection_id
    user_text = (message.text or "").strip()

    # 2) Matndan tashqari xabarlar (rasm, ovoz, stiker...)
    if not user_text:
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=NON_TEXT_REPLY,
                business_connection_id=conn_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Non-text javobda xatolik: %s", exc)
        return

    # 3) Token himoyasi: gigant xabarlarni qirqib tashlash
    if len(user_text) > USER_MESSAGE_MAX_CHARS:
        user_text = user_text[:USER_MESSAGE_MAX_CHARS]
        logger.info("user_id=%s xabari %d belgiga qisqartirildi", sender.id, USER_MESSAGE_MAX_CHARS)

    # 4) Flood-himoya: limit oshsa — jim o'tkazamiz (kvota tejaladi)
    if not flood_check(sender.id):
        logger.warning(
            "FLOOD limit: user_id=%s | %d msg / %d s",
            sender.id, FLOOD_LIMIT_MESSAGES, FLOOD_LIMIT_SECONDS,
        )
        return

    # 5) Asosiy biznes mantiq: AI javobini yaratish va yuborish
    try:
        # "typing..." indikatori — professional kayfiyat
        try:
            await bot.send_chat_action(
                chat_id=message.chat.id,
                action=ChatAction.TYPING,
                business_connection_id=conn_id,
            )
        except Exception:  # noqa: BLE001
            pass  # Indikator xatolik bo'lsa ham javob oqimi to'xtamaydi

        reply = await generate_ai_reply(sender.id, user_text)
        if not reply:
            reply = AI_FALLBACK_TEXT

        # MUHIM HARNESS DETALI:
        # AI matni ichida noto'g'ri HTML teglar uchrashi mumkin — shuning uchun
        # parse_mode=None bilan YAROQLI oddiy matn sifatida yuboramiz.
        await bot.send_message(
            chat_id=message.chat.id,
            text=reply[:TELEGRAM_MAX_CHARS],
            business_connection_id=conn_id,
            parse_mode=None,
        )
        logger.info("AI avto-javob yuborildi: user_id=%s", sender.id)
        cleanup_memory()

    except Exception as exc:  # noqa: BLE001
        logger.exception("AI javobda xatolik (user_id=%s): %s", sender.id, exc)
        # AI nogiron bo'lsa ham mijozni javobsiz qoldirmaslik — fallback
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=AI_FALLBACK_TEXT,
                business_connection_id=conn_id,
            )
        except Exception as inner:  # noqa: BLE001
            logger.exception("Zaxira javobda ham xatolik: %s", inner)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Botning o'ziga yozuvchilarga ma'lumot."""
    try:
        await message.answer(
            "👋 Men <b>Javohirbek Asqarovning AI-assistentiman</b>.\n\n"
            "Javohirbek haqidagi professional savollar (tajriba, ko'nikmalar, "
            "loyihalar) boʻyicha javob bera olaman.\n"
            "Shaxsiy suhbat uchun: @Dr_eviluz ✅"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("/start handlerida xatolik: %s", exc)


# ----------------------------------------------------------------------
# 7. HEALTH-CHECK WEB-SERVER (aiohttp)
# ----------------------------------------------------------------------
async def health_handler(request: web.Request) -> web.Response:
    """UptimeRobot / Render health-check: GET /  va  GET /health"""
    return web.json_response(
        {
            "status": "ok",
            "service": "javohirbek-ai-bot",
            "ai_model": AI_MODEL,
            "active_chats": len(chat_histories),
            "uptime_seconds": int(time.time() - STARTED_AT),
            "timestamp": int(time.time()),
        }
    )


async def start_web_server() -> web.AppRunner:
    """Yengil HTTP server: Render Port binding + Health-check."""
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=HOST, port=PORT)
    await site.start()
    logger.info("Health-check server ishga tushdi: http://%s:%s/health", HOST, PORT)
    return runner


# ----------------------------------------------------------------------
# 8. ASOSIY ENTRYPOINT: Bot polling + Web-server BIR event loop'da
# ----------------------------------------------------------------------
async def main() -> None:
    runner = await start_web_server()
    try:
        me = await bot.get_me()  # Token yaroqliligini fail-fast tekshirish
        logger.info("Bot avtorizatsiyadan o'tdi: @%s (id=%s)", me.username, me.id)
        logger.info("AI provayder: %s | model: %s", AI_BASE_URL, AI_MODEL)

        await bot.delete_webhook(drop_pending_updates=True)

        logger.info("Long-polling boshlanmoqda...")
        # start_polling business_message / business_connection update
        # turlarini avtomatik ruxsat etadi
        await dp.start_polling(bot)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Bot ishida kritik xatolik: %s", exc)
        raise
    finally:
        logger.info("Resurslar tozalanmoqda (graceful shutdown)...")
        await runner.cleanup()
        await bot.session.close()
        await ai_client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi. Xayr!")
