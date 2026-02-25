# Behruz Sokirov Music Bot

Telegram bot - ovozni MP3 ga aylantiradi.

---

## 🚀 Railway.app ga qo'yish (10 daqiqa)

### 1-qadam: GitHub account
1. https://github.com ga kiring
2. Agar account yo'q bo'lsa — "Sign up" bosing va ro'yxatdan o'ting

### 2-qadam: Git o'rnatish (agar yo'q bo'lsa)
1. https://git-scm.com/download/win dan yuklab oling
2. O'rnating (Next, Next, Install)

### 3-qadam: GitHub ga yuklash
CMD yoki PowerShell oching va yozing:

```
cd "c:\Users\hp\Desktop\ovoz+musiqa"
git init
git add .
git commit -m "first commit"
```

Keyin GitHub da yangi repo yarating:
1. https://github.com/new ga kiring
2. Repository name: `music-bot`
3. "Create repository" bosing
4. Ko'rsatilgan buyruqlarni nusxalang va CMD ga yozing

### 4-qadam: Railway.app
1. https://railway.app ga kiring
2. "Login with GitHub" bosing
3. "New Project" bosing
4. "Deploy from GitHub repo" tanlang
5. `music-bot` repo ni tanlang
6. Deploy tugashini kuting (2-3 daqiqa)

### 5-qadam: Environment Variables
Railway dashboard da:
1. Proyektni bosing
2. "Variables" tabini oching
3. "New Variable" bosing:
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: `8252338043:AAE708CJ-Slm_eZBMFsQio6NUue3aA99FCY`
4. Yana qo'shing:
   - Name: `DATA_DIR`
   - Value: `/app/data`

### 6-qadam: Volume (ma'lumotlar saqlanishi uchun)
1. "New" → "Volume" bosing
2. Mount Path: `/app/data`
3. "Create" bosing

### ✅ Tayyor!
Bot 24/7 ishlaydi. Railway ~$5/oy (usage-based).

---

## 📁 Fayllar
| Fayl | Vazifasi |
|------|----------|
| `main.py` | Asosiy bot kodi |
| `requirements.txt` | Python kutubxonalari |
| `Procfile` | Railway uchun start buyruq |
| `users.json` | Foydalanuvchilar bazasi |
| `audio_storage.json` | Kanal audiolari |
| `force_channels.json` | Majburiy obuna kanallari |

---

## 🔧 Admin buyruqlari
- `/admin` — Admin panel
- `/post` — Kanalga audio joylash
- `/sental` — Barchaga xabar yuborish
- `/stats` — Statistika
- `/forceset @kanal` — Majburiy obuna qo'shish
- `/forceclear` — Majburiy obunani o'chirish
