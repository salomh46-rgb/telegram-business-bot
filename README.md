# 🤖 Javohirbek AI — Telegram Business Javob Beruvchi Bot (24/7)

`aiogram 3.x` + `openai SDK (Gemini)` + `aiohttp` asosida qurilgan,
Telegram Business shaxsiy xabarlarga **Javohirbek Asqarov nomidan**
AI yordamida professional javob qaytaruvchi bot.
Render.com bepul tarifida UptimeRobot yordamida uzluksiz ishlaydi.

## 📁 Loyiha strukturasi

```
telegram-business-bot/
├── main.py            # Bot + AI qatlam + Web-server + Health-check
├── requirements.txt   # Aniq (pinned) kutubxona versiyalari
├── Procfile           # Render uchun ishga tushirish buyrug'i
├── .gitignore         # Keraksiz/maxfiy fayllarni chetlash
├── .env.example       # Muhit o'zgaruvchilari namunasi
└── README.md          # Shu fayl — deploy qo'llanmasi
```

## 🧠 AI arxitekturasi

- **Provayder-agnostik:** `openai` SDK + OpenAI-mos endpoint. Standart —
  Google Gemini **bepul** tarifi. OpenAI'ga o'tish: faqat 2 ta env o'zgartirasiz.
- **Suhbat xotirasi:** har bir foydalanuvchi uchun oxirgi 12 xabar eslab
  qolinadi (kontekstli javoblar: "Maosh kutilmangiz qanday?" — ai kontekst biladi).
- **Flood-himoya:** 60 soniyada 5 xabardan ortiq — API kvotani tejash uchun jim saqlab qo'yiladi.
- **SYSTEM_PROMPT:** `main.py` ichidagi bilim bazasi — tajriba, ko'nikmalar, loyihalar.

## 🚀 Deploy ketma-ketligi

1. **@BotFather**: `/newbot` → token; `Bot Settings` → **Business Mode** → **Enable**.
2. **Telegram Business**: Sozlamalar → Telegram Business → **Chatbots** → botni tanlang.
3. **Gemini AI kaliti** (BEPUL): [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   → "Create API key" → nusxalang.
4. **GitHub**: `git init && git add . && git commit -m "AI bot" && git push`.
5. **Render.com**: New → Web Service → reponi ulang → `Instance Type: Free`
   → Environment Variables:
   - `BOT_TOKEN = <BotFather tokeni>`
   - `AI_API_KEY = <Gemini kaliti>`
   - (`PORT` ni qo'l bilan YOZMASLIK kerak — Render o'zi beradi)
6. **UptimeRobot**: HTTP(s) monitor → `https://<app>.onrender.com/health`
   → Interval: **5 min** → Render 15-daqiqalik sleep'dan himoyalanadi.

## ✅ Tekshirish

```bash
curl https://<sizning-app>.onrender.com/health
# {"status":"ok","service":"javohirbek-ai-bot","ai_model":"gemini-3.6-flash", ...}
```

Keyin biznes akkauntingizga boshqa akkauntdan yozing: *"Assalomu alaykum,
Javohirbek qaysi texnologiyalarda ishlaydi?"* — bot AI javobini qaytarishi kerak.

## 🔧 OpenAI'ga o'tkazish (agar kerak bo'lsa)

Render Environment Variables'da:

```
AI_API_KEY=sk-...                 # platform.openai.com dan
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Kodda hech narsa o'zgartirish shart emas — hammasi env orqali boshqariladi.
