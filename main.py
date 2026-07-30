"""
=====================================================================
 TELEGRAM BUSINESS AUTO-REPLY BOT  (24/7 | Render.com Free Tier)
---------------------------------------------------------------------
 "Harness Engineering" qatlamlari:
   [1] BUSINESS LOGIC : aiogram 3.x  -> @dp.business_message() handler
   [2] INFRASTRUCTURE : aiohttp web  -> Render Port binding + /health
   [3] ENV & SAFETY   : os.getenv()  -> maxfiy kalitlar koddan tashqarida
   [4] OBSERVABILITY  : logging + try/except -> barqaror 24/7 ish rejimi
=====================================================================
"""

import asyncio
import logging
import os
import time
from typing import Dict

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BusinessConnection, Message

from dotenv import load_dotenv

# ----------------------------------------------------------------------
# 1. SOZLAMALAR (Environment Variables)
# ----------------------------------------------------------------------
load_dotenv()  # Lokal ishga tushirishda .env dan o'qiydi (Render'da env vars dashboarddan olinadi)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Render.com -> Environment Variables yoki "
        "lokal .env faylida sozlang."
    )

HOST: str = os.getenv("HOST", "0.0.0.0")
# Render.com PORT o'zgaruvchisini avtomatik beradi (masalan, 10000).
# Lokal ishga tushirishda 8080 ishlatiladi.
PORT: int = int(os.getenv("PORT", "8080"))

# Anti-spam: bitta foydalanuvchiga qayta avto-javob yuborishdan oldingi
# minimal oraliq (soniya). Standart: 6 soat = 21600.
REPLY_COOLDOWN_SECONDS: int = int(os.getenv("REPLY_COOLDOWN_SECONDS", "21600"))

AUTO_REPLY_TEXT: str = os.getenv(
    "AUTO_REPLY_TEXT",
    "👋 <b>Assalomu alaykum!</b>\n\n"
    "Xabaringiz qabul qilindi ✅\n"
    "Tez orada mutaxassis siz bilan bog'lanadi.\n\n"
    "🕒 Ish vaqtimiz: Du – Sha, 09:00–18:00",
)

# ----------------------------------------------------------------------
# 2. LOGGING (jarayonni kuzatish va xatolarni qayd etish)
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("business-bot")

# ----------------------------------------------------------------------
# 3. BOT & DISPATCHER
# ----------------------------------------------------------------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Yengil in-memory anti-spam xotirasi: user_id -> oxirgi javob vaqti (unix time)
last_replies: Dict[int, float] = {}
STARTED_AT = time.time()


# ----------------------------------------------------------------------
# 4. TELEGRAM HANDLERLAR
# ----------------------------------------------------------------------
@dp.business_connection()
async def on_business_connection(connection: BusinessConnection) -> None:
    """Botning biznes akkauntga ulanish holati o'zgarishini kuzatish (Logging)."""
    state = "✅ UZANDI" if connection.is_enabled else "⛔ O'CHIRILDI"
    logger.info(
        "Business connection: %s | user_id=%s | can_reply=%s",
        state,
        connection.user.id,
        connection.can_reply,
    )


@dp.business_message()
async def handle_business_message(message: Message) -> None:
    """Telegram Business orqali kelgan SHAXSIY xabarlarga avto-javob."""
    sender = message.from_user

    # 1) Infinite loop himoyasi: botlarga/o'ziga javob bermaslik
    if sender is None or sender.is_bot:
        return

    now = time.time()

    # 2) Anti-spam filtri: cooldown niqob ostidan o'tmagan bo'lsa, jim turish
    last = last_replies.get(sender.id, 0.0)
    if now - last < REPLY_COOLDOWN_SECONDS:
        logger.info("Cooldown faol: user_id=%s ga takroriy javob yuborilmadi", sender.id)
        return

    # 3) Asosiy biznes mantiq: chiroyli formatda avto-javob
    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=AUTO_REPLY_TEXT,
            # MUHIM: business_connection_id berilmasa, javob oddiy bot
            # nomidan qochadi, biznes akkaunt nomidan yuborilishi kerak!
            business_connection_id=message.business_connection_id,
        )
        last_replies[sender.id] = now
        logger.info(
            "Avto-javob yuborildi: user_id=%s | username=@%s",
            sender.id,
            sender.username or "—",
        )

        # 4) In-memory lug'at cheksiz o'sib ketmasligi uchun davriy tozalash
        if len(last_replies) > 10_000:
            cutoff = now - REPLY_COOLDOWN_SECONDS
            stale = [uid for uid, ts in last_replies.items() if ts < cutoff]
            for uid in stale:
                last_replies.pop(uid, None)
            logger.info("Anti-spam xotira tozalandi: %d ta eski yozuv o'chirildi", len(stale))

    except Exception as exc:  # noqa: BLE001 - har qanday kutilmagan xatoni qayd etamiz
        # Bot "yiqilib" ketmasligi uchun xatoni yutib, faqat logga yozamiz
        logger.exception("Avto-javob yuborishda xatolik (user_id=%s): %s", sender.id, exc)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Botga to'g'ridan-to'g'ri yozuvchilarga ma'lumot berish."""
    try:
        await message.answer(
            "👋 Bu bot <b>Telegram Business</b> akkauntiga ulangan "
            "avto-javob beruvchi hisoblanadi.\n\n"
            "Biznes bo'yicha murojaat qilmoqchi bo'lsangiz, bizning biznes "
            "akkauntga yozing — bot sizga doimo javob qaytaradi ✅"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("/start handlerida xatolik: %s", exc)


# ----------------------------------------------------------------------
# 5. HEALTH-CHECK WEB-SERVER (aiohttp)
# ----------------------------------------------------------------------
async def health_handler(request: web.Request) -> web.Response:
    """UptimeRobot / Render health-check endpoint: GET /  va  GET /health"""
    return web.json_response(
        {
            "status": "ok",
            "service": "telegram-business-bot",
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
# 6. ASOSIY ENTRYPOINT: Bot polling + Web-server BIR event loop'da
# ----------------------------------------------------------------------
async def main() -> None:
    runner = await start_web_server()
    try:
        # Token yaroqliligini oldindan tekshirish (fail-fast)
        me = await bot.get_me()
        logger.info("Bot avtorizatsiyadan o'tdi: @%s (id=%s)", me.username, me.id)

        # Avval webhook o'rnatilgan bo'lsa, polling'ga xalaqit bermasligi
        # uchun o'chiramiz
        await bot.delete_webhook(drop_pending_updates=True)

        logger.info("Long-polling boshlanmoqda...")
        # start_polling barcha kerakli update turlarini (jumladan,
        # business_message va business_connection) avtomatik ruxsat etadi
        await dp.start_polling(bot)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Bot ishida kritik xatolik: %s", exc)
        raise
    finally:
        logger.info("Resurslar tozalanmoqda (graceful shutdown)...")
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi. Xayr!")
