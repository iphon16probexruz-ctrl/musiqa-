# 🚀 Railway ga qo'yish (5 daqiqa)

## 1-qadam: Git o'rnatish

**Git o'rnatilmagan bo'lsa:**

1. https://git-scm.com/download/win oching
2. "Download for Windows" bosing
3. Yuklangan faylni oching va o'rnating:
   - Hamma joyda **Next** bosing (default sozlamalar)
   - **Install** bosing
   - **Finish** bosing

---

## 2-qadam: GitHub ga yuklash

**Usul 1: Avtomatik (oson)**

1. `deploy.bat` faylini **ikki marta** bosing
2. Agar Git o'rnatilmagan bo'lsa — xato chiqadi, Git ni o'rnating
3. Agar GitHub login so'rasa — username va parol kiriting

**Usul 2: Qo'lda**

CMD yoki PowerShell oching va yozing:

```
cd "c:\Users\hp\Desktop\ovoz+musiqa"
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/iphon16probexruz-ctrl/music-bot.git
git push -u origin main
```

---

## 3-qadam: Railway ga qo'yish

1. **https://railway.app** ga kiring
2. **"Login with GitHub"** bosing
3. **"New Project"** bosing
4. **"Deploy from GitHub repo"** tanlang
5. **`music-bot`** repo ni tanlang
6. Deploy tugashini kuting (2-3 daqiqa)

---

## 4-qadam: Environment Variables

Railway dashboard da:

1. Proyektni bosing
2. **"Variables"** tabini oching
3. **"New Variable"** bosing va qo'shing:

   **Variable 1:**
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: `8252338043:AAE708CJ-Slm_eZBMFsQio6NUue3aA99FCY`

   **Variable 2:**
   - Name: `DATA_DIR`
   - Value: `/app/data`

4. **"Add"** bosing

---

## 5-qadam: Volume (ma'lumotlar saqlanishi uchun)

1. Railway dashboard da **"New"** bosing
2. **"Volume"** tanlang
3. **Mount Path:** `/app/data`
4. **"Create"** bosing

---

## ✅ Tayyor!

Bot 24/7 ishlaydi. Railway ~$5/oy oladi (usage-based).

**Tekshirish:**
- Botga `/start` yuboring
- Agar javob bersa — ishlayapti! 🎉

---

## Xatoliklar

**"git is not recognized"**
→ Git o'rnatilmagan. 1-qadamni bajaring.

**"Authentication failed"**
→ GitHub login/parol noto'g'ri. GitHub ga kiring va tekshiring.

**"Repository not found"**
→ Repo nomi noto'g'ri. GitHub da `music-bot` repo borligini tekshiring.

**Bot ishlamayapti**
→ Railway Variables tekshiring (`TELEGRAM_BOT_TOKEN` va `DATA_DIR`).
