#!/usr/bin/env python3
"""
Railway deployment tekshiruv skripti
"""
import os
import json

print("=" * 50)
print("Railway Deployment Tekshiruv")
print("=" * 50)
print()

# 1. Fayllar tekshiruvi
required_files = [
    "main.py",
    "requirements.txt",
    "Procfile",
    "runtime.txt",
    ".gitignore",
]

print("1. Fayllar tekshirilmoqda...")
missing = []
for f in required_files:
    if os.path.exists(f):
        print(f"  [OK] {f}")
    else:
        print(f"  [X] {f} - TOPILMADI!")
        missing.append(f)

if missing:
    print(f"\n[!] {len(missing)} ta fayl topilmadi!")
else:
    print("\n[OK] Barcha fayllar mavjud!")

print()

# 2. requirements.txt tekshiruvi
print("2. requirements.txt tekshirilmoqda...")
try:
    with open("requirements.txt", "r") as f:
        reqs = f.read().strip()
    if "aiogram" in reqs:
        print("  [OK] aiogram topildi")
    else:
        print("  [X] aiogram topilmadi!")
    if "imageio-ffmpeg" in reqs:
        print("  [OK] imageio-ffmpeg topildi")
    else:
        print("  [X] imageio-ffmpeg topilmadi!")
except Exception as e:
    print(f"  ❌ Xato: {e}")

print()

# 3. Procfile tekshiruvi
print("3. Procfile tekshirilmoqda...")
try:
    with open("Procfile", "r") as f:
        procfile = f.read().strip()
    if "python main.py" in procfile:
        print("  [OK] Procfile to'g'ri")
    else:
        print(f"  [!] Procfile: {procfile}")
except Exception as e:
    print(f"  ❌ Xato: {e}")

print()

# 4. main.py tekshiruvi
print("4. main.py tekshirilmoqda...")
try:
    with open("main.py", "r", encoding="utf-8") as f:
        code = f.read()
    
    checks = [
        ("TOKEN = os.getenv", "Environment variable o'qish"),
        ("DATA_DIR = os.getenv", "DATA_DIR sozlash"),
        ("async def main()", "main() funksiya"),
        ("asyncio.run(main())", "Bot ishga tushirish"),
        ("aiogram", "aiogram import"),
    ]
    
    for check, desc in checks:
        if check in code:
            print(f"  [OK] {desc}")
        else:
            print(f"  [X] {desc} - topilmadi!")
except Exception as e:
    print(f"  ❌ Xato: {e}")

print()

# 5. Environment variables
print("5. Environment Variables (Railway da qo'shish kerak):")
print("  TELEGRAM_BOT_TOKEN = 8252338043:AAE708CJ-Slm_eZBMFsQio6NUue3aA99FCY")
print("  DATA_DIR = /app/data")
print()

# 6. Yakuniy xulosa
print("=" * 50)
if not missing:
    print("[OK] Barcha fayllar tayyor!")
    print("\nKeyingi qadamlar:")
    print("  1. Railway.app ga kiring")
    print("  2. 'Deploy from GitHub repo' tanlang")
    print("  3. music-bot repo ni tanlang")
    print("  4. Variables qo'shing (yuqorida ko'rsatilgan)")
    print("  5. Volume qo'shing: /app/data")
    print("  6. Bot ishlaydi!")
else:
    print("[!] Ba'zi fayllar topilmadi. Iltimos, tekshiring.")
print("=" * 50)
