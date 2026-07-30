# 🤖 Telegram Business Auto-Reply Bot (24/7 — Render.com Free Tier)

`aiogram 3.x` + `aiohttp` asosida qurilgan, Telegram Business shaxsiy xabarlarga
avtomatik javob qaytaruvchi, Render.com bepul tarifida UptimeRobot yordamida
uzluksiz ishlaydigan professional bot.

## 📁 Loyiha strukturasi

```
telegram-business-bot/
├── main.py            # Bot + Web-server + Health-check + Business handlerlar
├── requirements.txt   # Aniq (pinned) kutubxona versiyalari
├── Procfile           # Render uchun ishga tushirish buyrug'i
├── .gitignore         # Keraksiz/maxfiy fayllarni chetlash
├── .env.example       # Muhit o'zgaruvchilari namunasi
└── README.md          # Shu fayl — deploy qo'llanmasi
```

## ⚡ Muhim arxitektura qarorlari

| Qatlam | Yechim | Sababi |
|---|---|---|
| Business logic | `@dp.business_message()` | Telegram Business biznes xabarlarini qabul qiladi |
| Javob | `business_connection_id=...` | Javob **biznes akkaunt nomidan** yuboriladi, shart! |
| Health-check | `aiohttp` — `/` va `/health` | Render port scanning + UptimeRobot ping |
| Concurrency | Bitta `asyncio.run()` ichida polling + web-site | Ikki jarayon bir event-loop'da xatosiz |
| Secrets | `os.getenv()` (`.env` lokalda) | Kod bazasida hech qanday token yo'q |
| Anti-spam | In-memory cooldown (6 soat) | Bir foydalanuvchiga spam yuborilmaydi |

## 🚀 Deploy ketma-ketligi (qisqa)

1. **@BotFather**: `/newbot` → token oling; `Bot Settings` → **Business Mode** → **Enable**.
2. **Telegram Business**: Sozlamalar → Telegram Business → **Chatbots** → botni tanlang.
3. **GitHub**: `git init && git add . && git commit -m "init" && git push`.
4. **Render.com**: New → Web Service → reponi ulang → `Instance Type: Free`
   → Environment Variable sifatida faqat `BOT_TOKEN` qo'shing (PORT auto).
5. **UptimeRobot**: HTTP(s) monitor → `https://<app>.onrender.com/health`
   → Interval: **5 min** → Render 15 daqiqalik sleep'dan hech qachon uxlamaydi.

## ✅ Tekshirish

```bash
curl https://<sizning-app>.onrender.com/health
# {"status": "ok", "service": "telegram-business-bot", "uptime_seconds": 1234, ...}
```
