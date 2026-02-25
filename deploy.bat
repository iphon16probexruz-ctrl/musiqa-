@echo off
echo ========================================
echo GitHub ga yuklash...
echo ========================================

cd /d "%~dp0"

echo.
echo 1. Git tekshirilmoqda...
git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [XATO] Git o'rnatilmagan!
    echo.
    echo Iltimos, avval Git o'rnating:
    echo https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo [OK] Git topildi!
echo.

echo 2. Repository yaratilmoqda...
git init
if errorlevel 1 (
    echo [XATO] git init ishlamadi
    pause
    exit /b 1
)

echo [OK] Repository yaratildi
echo.

echo 3. Fayllar qo'shilmoqda...
git add .
if errorlevel 1 (
    echo [XATO] git add ishlamadi
    pause
    exit /b 1
)

echo [OK] Fayllar qo'shildi
echo.

echo 4. Commit qilinmoqda...
git commit -m "Deploy to Railway"
if errorlevel 1 (
    echo [XATO] git commit ishlamadi
    pause
    exit /b 1
)

echo [OK] Commit qilindi
echo.

echo 5. Branch nomi o'zgartirilmoqda...
git branch -M main
if errorlevel 1 (
    echo [XATO] git branch ishlamadi
    pause
    exit /b 1
)

echo [OK] Branch main ga o'zgartirildi
echo.

echo 6. Remote qo'shilmoqda...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/iphon16probexruz-ctrl/music-bot.git
if errorlevel 1 (
    echo [XATO] git remote add ishlamadi
    pause
    exit /b 1
)

echo [OK] Remote qo'shildi
echo.

echo 7. GitHub ga yuborilmoqda...
echo (GitHub login/parol so'rashi mumkin)
git push -u origin main
if errorlevel 1 (
    echo.
    echo [XATO] git push ishlamadi
    echo.
    echo Ehtimol:
    echo - GitHub login/parol noto'g'ri
    echo - Internet aloqasi yo'q
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Kod GitHub ga yuklandi!
echo ========================================
echo.
echo Endi Railway.app ga kiring va repo ni tanlang.
echo.
pause
