import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberOwner,
    ChatMemberAdministrator, ChatMemberMember, ChatMemberRestricted
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Token - Railway da environment variable dan olinadi
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    # Local test uchun fallback
    TOKEN = "8252338043:AAE708CJ-Slm_eZBMFsQio6NUue3aA99FCY"

# Kanal
CHANNEL_ID = os.getenv("CHANNEL_ID", "@Uzbek_goloslar1")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/Uzbek_goloslar1")

# Admin ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "6374979572"))

# Storage files (DATA_DIR dan o'qiydi - hosting uchun)
DATA_DIR = os.getenv("DATA_DIR", ".")  # Railway: /app/data
AUDIO_STORAGE_FILE = os.path.join(DATA_DIR, "audio_storage.json")
FORCE_CHANNELS_FILE = os.path.join(DATA_DIR, "force_channels.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

logger.info(f"DATA_DIR: {DATA_DIR}")
logger.info(f"AUDIO_STORAGE_FILE: {AUDIO_STORAGE_FILE}")
logger.info(f"USERS_FILE: {USERS_FILE}")

# DATA_DIR mavjud bo'lmasa yaratish
try:
    if DATA_DIR != "." and not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        logger.info(f"Created DATA_DIR: {DATA_DIR}")
except Exception as e:
    logger.error(f"Error creating DATA_DIR: {e}")

# Router
router = Router()

# User data storage (for regular users)
user_data_storage: Dict[int, dict] = {}


# ============== USERS DATABASE ==============
def load_users() -> Dict:
    """Barcha foydalanuvchilarni yuklash"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_users(data: Dict):
    """Foydalanuvchilarni saqlash"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_user(user_id: int, username: str = None, first_name: str = None):
    """Yangi foydalanuvchini qo'shish yoki yangilash"""
    try:
        users = load_users()
        user_id_str = str(user_id)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if user_id_str not in users:
            users[user_id_str] = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "joined_at": now,
                "last_active": now,
            }
            logger.info(f"New user added: {user_id} (@{username})")
        else:
            users[user_id_str]["username"] = username
            users[user_id_str]["first_name"] = first_name
            users[user_id_str]["last_active"] = now
        
        save_users(users)
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")


def get_all_user_ids() -> List[int]:
    """Barcha foydalanuvchi ID larini olish"""
    users = load_users()
    return [int(uid) for uid in users.keys()]


def get_users_count() -> int:
    """Foydalanuvchilar sonini olish"""
    return len(load_users())


# ============== FSM STATES ==============
class AdminPostStates(StatesGroup):
    waiting_audio = State()
    waiting_songname = State()
    waiting_posttext = State()


class AdminSentalStates(StatesGroup):
    waiting_message = State()


class UserStates(StatesGroup):
    waiting_line1 = State()
    waiting_photo = State()


# ============== STORAGE FUNCTIONS ==============
def load_audio_storage() -> Dict:
    if os.path.exists(AUDIO_STORAGE_FILE):
        with open(AUDIO_STORAGE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_audio_storage(data: Dict):
    with open(AUDIO_STORAGE_FILE, "w") as f:
        json.dump(data, f)


def _normalize_channel_ref(ref: str) -> str:
    ref = (ref or "").strip()
    if not ref:
        return ref
    if ref.startswith("@"):
        return ref
    if ref.lstrip("-").isdigit():
        return ref
    return "@" + ref


def load_force_channels() -> List[str]:
    """Majburiy kanallar ro'yxati (max 5)."""
    legacy = "force_channel.txt"
    if os.path.exists(legacy) and not os.path.exists(FORCE_CHANNELS_FILE):
        with open(legacy, "r", encoding="utf-8") as f:
            one = _normalize_channel_ref(f.read().strip())
        if one:
            with open(FORCE_CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump([one], f)
        try:
            os.remove(legacy)
        except Exception:
            pass

    if os.path.exists(FORCE_CHANNELS_FILE):
        try:
            with open(FORCE_CHANNELS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                out = [_normalize_channel_ref(x) for x in data if str(x).strip()]
                seen = set()
                res = []
                for x in out:
                    if x and x not in seen:
                        seen.add(x)
                        res.append(x)
                return res[:5]
        except Exception:
            return []
    return []


def save_force_channels(channels: List[str]) -> None:
    channels = [_normalize_channel_ref(x) for x in (channels or [])]
    seen = set()
    res = []
    for x in channels:
        if x and x not in seen:
            seen.add(x)
            res.append(x)
    with open(FORCE_CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(res[:5], f, ensure_ascii=False)


def add_force_channel(ref: str) -> tuple:
    """Returns (ok, message)."""
    ref = _normalize_channel_ref(ref)
    if not ref:
        return False, "Kanal noto'g'ri."
    channels = load_force_channels()
    if ref in channels:
        return True, "Bu kanal allaqachon qo'shilgan."
    if len(channels) >= 5:
        return False, "Max 5 ta kanal bo'ladi. Avval bittasini o'chiring."
    channels.append(ref)
    save_force_channels(channels)
    return True, f"Qo'shildi: {ref}"


def remove_force_channel(ref: str) -> tuple:
    ref = _normalize_channel_ref(ref)
    channels = load_force_channels()
    if not channels:
        return False, "Majburiy kanal yo'q."
    if ref == "all":
        save_force_channels([])
        return True, "Barchasi o'chirildi."
    if ref not in channels:
        return False, "Bu kanal ro'yxatda yo'q."
    channels = [x for x in channels if x != ref]
    save_force_channels(channels)
    return True, f"O'chirildi: {ref}"


def clear_force_channels() -> None:
    save_force_channels([])


def get_ffmpeg_path():
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except:
        return "ffmpeg"


# ============== FORCE SUBSCRIBE ==============
async def check_force_subscribe(user_id: int, bot: Bot) -> bool:
    if user_id == ADMIN_ID:
        return True

    channels = load_force_channels()
    if not channels:
        return True

    ALLOWED_TYPES = (
        ChatMemberOwner,
        ChatMemberAdministrator,
        ChatMemberMember,
        ChatMemberRestricted,
    )

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if not isinstance(member, ALLOWED_TYPES):
                return False
        except Exception as e:
            print(f"Force check error for {ch}: {e}")
            return False
    return True


def build_force_join_keyboard(pending_audio_id: Optional[str] = None) -> InlineKeyboardMarkup:
    channels = load_force_channels()
    rows = []
    for ch in channels:
        if ch.startswith("@"):
            url = f"https://t.me/{ch[1:]}"
            label = ch
        else:
            url = CHANNEL_LINK
            label = "Kanal"
        rows.append([InlineKeyboardButton(text=f"📢 Obuna bo'lish: {label}", url=url)])
    
    if pending_audio_id:
        rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data=f"chkjoin:{pending_audio_id}")])
    else:
        rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="chkjoin:start")])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else InlineKeyboardMarkup(inline_keyboard=[])


# ============== CONVERT TO MP3 ==============
async def convert_to_mp3(file_id: str, bot: Bot) -> bytes:
    """Voice/audio ni MP3 ga aylantirish"""
    file = await bot.get_file(file_id)
    temp_dir = tempfile.gettempdir()
    ext = ""
    try:
        ext = os.path.splitext(file.file_path or "")[1]
    except Exception:
        ext = ""
    if not ext:
        ext = ".ogg"
    input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}{ext}")
    output_path = os.path.join(temp_dir, f"output_{uuid.uuid4()}.mp3")
    
    await bot.download_file(file.file_path, input_path)
    
    ffmpeg = get_ffmpeg_path()
    subprocess.run([
        ffmpeg, "-i", input_path,
        "-codec:a", "libmp3lame",
        "-b:a", "192k",
        "-y", output_path
    ], check=True, capture_output=True, timeout=30)
    
    with open(output_path, "rb") as f:
        mp3_data = f.read()
    
    try:
        os.remove(input_path)
        os.remove(output_path)
    except:
        pass
    
    return mp3_data


async def send_with_progress(message: Message, bot: Bot, file_id: str, title: str = ""):
    """10 sekund progress bilan MP3 yuborish"""
    
    progress_msgs = [
        ("🎵 *Qabul qilindi!*\n\n✨ _Tayyorlanmoqda..._\n\n⏳ [░░░░░░░░░░] 0%", 0),
        ("🎵 *Qabul qilindi!*\n\n🎼 _Qayta ishlanmoqda..._\n\n⏳ [██░░░░░░░░] 20%", 2),
        ("🎵 *Qabul qilindi!*\n\n🎧 _Sifat oshirilmoqda..._\n\n⏳ [████░░░░░░] 40%", 2),
        ("🎵 *Qabul qilindi!*\n\n🎨 _Bezatilmoqda..._\n\n⏳ [██████░░░░] 60%", 2),
        ("🎵 *Qabul qilindi!*\n\n✅ _Yakunlanmoqda..._\n\n⏳ [████████░░] 80%", 2),
        ("🎵 *Tayyor!*\n\n🎉 _Yuklanmoqda..._\n\n⏳ [██████████] 100%", 2),
    ]
    
    progress_msg = await message.answer(
        progress_msgs[0][0],
        parse_mode=ParseMode.MARKDOWN
    )
    
    for i in range(1, len(progress_msgs)):
        await asyncio.sleep(progress_msgs[i][1])
        try:
            await progress_msg.edit_text(
                progress_msgs[i][0],
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    try:
        await progress_msg.delete()
    except:
        pass
    
    try:
        mp3_data = await convert_to_mp3(file_id, bot)
        
        second_line = "@Uzbek_goloslar1"
        if title:
            caption = f"❤️\n{title}\n{second_line}"
        else:
            caption = f"❤️\n{second_line}"
        
        await message.answer_audio(
            audio=BufferedInputFile(mp3_data, filename="audio.mp3"),
            title=title if title else "Audio",
            performer="@Uzbek_goloslar1",
            caption=caption,
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:100]}")


# ============== START COMMAND ==============
@router.message(CommandStart())
async def start_command(message: Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    
    # Foydalanuvchini bazaga qo'shish
    add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # Check if there's an audio parameter (from channel button)
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if args:
        audio_id = args[0]
        storage = load_audio_storage()
        
        if audio_id in storage:
            audio_data = storage[audio_id]
            file_id = audio_data.get("file_id")
            title = audio_data.get("title", "")
            
            if not await check_force_subscribe(user_id, bot):
                kb = build_force_join_keyboard(pending_audio_id=audio_id)
                await message.answer(
                    "⚠️ *Avval kanallarga obuna bo'ling, keyin \"Tekshirish\" ni bosing!*",
                    reply_markup=kb,
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            await send_with_progress(message, bot, file_id, title)
            return

    # Check force channel (normal start)
    if not await check_force_subscribe(user_id, bot):
        kb = build_force_join_keyboard()
        await message.answer(
            "⚠️ *Botdan foydalanish uchun kanalga obuna bo'ling!*\n\n"
            "Obuna bo'lgach, pastdagi *Tekshirish* tugmasini bosing.",
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Normal start - show welcome
    if user_id == ADMIN_ID:
        await message.answer(
            "🔐 *Admin Panel*\n\n"
            "/admin - Admin panel ochish\n"
            "/post - Kanalga e'lon\n"
            "/sental - Barchaga xabar yuborish\n"
            "/forceset @kanal - Majburiy kanal\n"
            "/forceclear - O'chirish\n"
            "/stats - Statistika",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(
            "🎵 *Xush kelibsiz!*\n\n"
            "Ovoz yuboring - musiqa qilib beraman!",
            parse_mode=ParseMode.MARKDOWN
        )


@router.message(Command("admin"))
async def admin_panel_command(message: Message):
    """Admin panelni ochish (faqat ADMIN_ID)."""
    if message.from_user.id != ADMIN_ID:
        return

    users_count = get_users_count()
    await message.answer(
        f"🔐 *Admin panel*\n\n"
        f"👥 Foydalanuvchilar: *{users_count}* ta\n\n"
        "📢 Kanalga post: `/post`\n"
        "📨 Barchaga xabar: `/sental`\n"
        "⚙️ Majburiy kanal: `/forceset @kanal`\n"
        "🗑 Kanalni o'chirish: `/forceclear`\n"
        "📊 Statistika: `/stats`\n\n"
        "Eslatma: Admin ham oddiy foydalanuvchi kabi voice yuborib MP3 olishi mumkin.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ============== REGULAR USER VOICE ==============
@router.message(F.voice)
async def handle_user_voice(message: Message, bot: Bot, state: FSMContext):
    """Oddiy foydalanuvchi voice yuborsa"""
    user_id = message.from_user.id
    
    # Foydalanuvchini bazaga qo'shish
    add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # Check if admin is in post flow
    current_state = await state.get_state()
    if current_state == AdminPostStates.waiting_audio.state and user_id == ADMIN_ID:
        await admin_receive_audio(message, bot, state)
        return
    
    # Check force subscribe
    if not await check_force_subscribe(user_id, bot):
        kb = build_force_join_keyboard()
        await message.answer(
            "⚠️ *Botdan foydalanish uchun kanalga obuna bo'ling!*",
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    voice = message.voice
    if not voice:
        return
    
    # Save voice file_id
    user_data_storage[user_id] = {
        "file_id": voice.file_id,
        "duration": voice.duration,
    }
    
    await message.answer(
        "✅ *Ovoz qabul qilindi!*\n\n"
        "📝 *Qo'shiq nomini* yozing:",
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(UserStates.waiting_line1)


@router.message(UserStates.waiting_line1, F.text)
async def get_line1_from_user(message: Message, state: FSMContext):
    """Foydalanuvchidan 1-qator (qo'shiq nomi)"""
    user_id = message.from_user.id
    line1 = message.text.strip()
    
    if user_id not in user_data_storage:
        await message.answer("❌ Avval ovoz yuboring!")
        await state.clear()
        return

    user_data_storage[user_id]["line1"] = line1
    await message.answer(
        "🖼 *Rasm yuboring* yoki /skip bosing:",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(UserStates.waiting_photo)


@router.message(UserStates.waiting_photo, Command("skip"))
async def user_skip_photo(message: Message, bot: Bot, state: FSMContext):
    """Rasmni o'tkazib yuborish"""
    user_id = message.from_user.id
    if user_id not in user_data_storage:
        await message.answer("❌ Avval ovoz yuboring!")
        await state.clear()
        return

    user_data_storage[user_id]["photo_path"] = None
    await finalize_user_track(message, bot, user_id)
    await state.clear()


@router.message(UserStates.waiting_photo, F.photo)
async def user_receive_photo(message: Message, bot: Bot, state: FSMContext):
    """Rasm qabul qilish"""
    user_id = message.from_user.id
    if user_id not in user_data_storage:
        await message.answer("❌ Avval ovoz yuboring!")
        await state.clear()
        return

    if not message.photo:
        await message.answer("❌ Rasm yuboring yoki /skip bosing.")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_dir = tempfile.gettempdir()
    photo_path = os.path.join(temp_dir, f"user_photo_{user_id}_{photo.file_id}.jpg")
    await bot.download_file(file.file_path, photo_path)
    user_data_storage[user_id]["photo_path"] = photo_path
    await finalize_user_track(message, bot, user_id)
    await state.clear()


async def finalize_user_track(message: Message, bot: Bot, user_id: int) -> None:
    """User trackni progress bilan tayyorlab yuborish."""
    data = user_data_storage.get(user_id) or {}
    file_id = data.get("file_id")
    line1 = (data.get("line1") or "").strip()
    photo_path = data.get("photo_path")

    if not file_id:
        await message.answer("❌ Xatolik: audio topilmadi.")
        return

    progress_msgs = [
        ("🎵 *Qabul qilindi!*\n\n✨ _Tayyorlanmoqda..._\n\n⏳ [░░░░░░░░░░] 0%", 0),
        ("🎵 *Qabul qilindi!*\n\n🎼 _Qayta ishlanmoqda..._\n\n⏳ [██░░░░░░░░] 20%", 2),
        ("🎵 *Qabul qilindi!*\n\n🎧 _Sifat oshirilmoqda..._\n\n⏳ [████░░░░░░] 40%", 2),
        ("🎵 *Qabul qilindi!*\n\n🎨 _Bezatilmoqda..._\n\n⏳ [██████░░░░] 60%", 2),
        ("🎵 *Qabul qilindi!*\n\n✅ _Yakunlanmoqda..._\n\n⏳ [████████░░] 80%", 2),
        ("🎵 *Tayyor!*\n\n🎉 _Yuklanmoqda..._\n\n⏳ [██████████] 100%", 2),
    ]

    progress_msg = await message.answer(progress_msgs[0][0], parse_mode=ParseMode.MARKDOWN)
    for i in range(1, len(progress_msgs)):
        await asyncio.sleep(progress_msgs[i][1])
        try:
            await progress_msg.edit_text(progress_msgs[i][0], parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
    try:
        await progress_msg.delete()
    except Exception:
        pass

    try:
        mp3_data = await convert_to_mp3(file_id, bot)
        caption_parts = ["❤️"]
        if line1:
            caption_parts.append(line1)
        caption_parts.append(CHANNEL_LINK)
        caption = "\n".join(caption_parts)

        if photo_path and os.path.exists(photo_path):
            with open(photo_path, "rb") as thumb:
                thumb_data = thumb.read()
            await message.answer_audio(
                audio=BufferedInputFile(mp3_data, filename="audio.mp3"),
                title=line1 if line1 else "Audio",
                performer="@Uzbek_goloslar1",
                caption=caption,
                thumbnail=BufferedInputFile(thumb_data, filename="thumb.jpg"),
            )
        else:
            await message.answer_audio(
                audio=BufferedInputFile(mp3_data, filename="audio.mp3"),
                title=line1 if line1 else "Audio",
                performer="@Uzbek_goloslar1",
                caption=caption,
            )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:100]}")
    finally:
        try:
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
        except Exception:
            pass
        user_data_storage.pop(user_id, None)


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in user_data_storage:
        del user_data_storage[user_id]
    await state.clear()
    await message.answer("❌ Bekor qilindi", parse_mode=ParseMode.MARKDOWN)


# ============== ADMIN COMMANDS ==============
@router.message(Command("post"))
async def post_command(message: Message, state: FSMContext):
    """Kanalga e'lon"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "🎵 *Kanalga e'lon*\n\n"
        "1) Audio yuboring (voice yoki MP3) — kanalda qanday bo'lsa shunday chiqadi.\n"
        "2) Keyin *qo'shiq nomi*ni so'rayman.\n"
        "3) Keyin kanalga birga chiqadigan *xabar matni*ni so'rayman (link bo'lsa ham bo'ladi).\n\n"
        "Bekor: /cancel",
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(AdminPostStates.waiting_audio)


@router.message(AdminPostStates.waiting_audio, F.audio)
async def admin_receive_audio(message: Message, bot: Bot, state: FSMContext):
    """Admin /post ichida audio qabul qilish"""
    if message.from_user.id != ADMIN_ID:
        return

    kind = None
    file_id = None
    duration = None
    caption_prefill = (message.caption or "").strip()
    caption_entities_prefill = message.caption_entities or []

    if message.voice:
        kind = "voice"
        file_id = message.voice.file_id
        duration = message.voice.duration
    elif message.audio:
        kind = "audio"
        file_id = message.audio.file_id
        duration = message.audio.duration
    else:
        await message.answer("❌ *Audio yuboring (voice yoki MP3).*", parse_mode=ParseMode.MARKDOWN)
        return

    await state.update_data(
        post_kind=kind,
        post_file_id=file_id,
        post_duration=duration,
        post_text_prefill=caption_prefill if caption_prefill else None,
        post_text_entities_prefill=caption_entities_prefill if caption_prefill else None,
    )

    await message.answer(
        "✅ *Audio qabul qilindi.*\n\n"
        "📝 *1) Qo'shiq nomini yuboring* (alohida):",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(AdminPostStates.waiting_songname)


# Handle voice in admin post state
@router.message(AdminPostStates.waiting_audio, F.voice)
async def admin_receive_voice(message: Message, bot: Bot, state: FSMContext):
    """Admin /post ichida voice qabul qilish"""
    if message.from_user.id != ADMIN_ID:
        return

    caption_prefill = (message.caption or "").strip()
    caption_entities_prefill = message.caption_entities or []

    await state.update_data(
        post_kind="voice",
        post_file_id=message.voice.file_id,
        post_duration=message.voice.duration,
        post_text_prefill=caption_prefill if caption_prefill else None,
        post_text_entities_prefill=caption_entities_prefill if caption_prefill else None,
    )

    await message.answer(
        "✅ *Audio qabul qilindi.*\n\n"
        "📝 *1) Qo'shiq nomini yuboring* (alohida):",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(AdminPostStates.waiting_songname)


@router.message(AdminPostStates.waiting_songname, F.text)
async def admin_receive_songname(message: Message, bot: Bot, state: FSMContext):
    """Admin /post ichida qo'shiq nomini qabul qilish"""
    if message.from_user.id != ADMIN_ID:
        return

    songname = message.text.strip()
    if not songname:
        await message.answer("❌ *Qo'shiq nomini yuboring.*", parse_mode=ParseMode.MARKDOWN)
        return

    data = await state.get_data()
    await state.update_data(post_songname=songname)

    # Agar audio bilan caption kelgan bo'lsa, post matnini yana so'ramaymiz
    if data.get("post_text_prefill"):
        await state.update_data(post_text=data.get("post_text_prefill"))
        await admin_finalize_post(message, bot, state)
        return

    await message.answer(
        "📝 *2) Kanalga birga chiqadigan xabarni yuboring.*\n"
        "Link bo'lsa ham bo'ladi (xuddi shunday chiqadi).",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(AdminPostStates.waiting_posttext)


@router.message(AdminPostStates.waiting_posttext, F.text)
async def admin_receive_posttext(message: Message, bot: Bot, state: FSMContext):
    """Admin /post ichida kanalga chiqadigan xabar matnini qabul qilish"""
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.strip()
    if not text:
        await message.answer("❌ *Xabar matnini yuboring.*", parse_mode=ParseMode.MARKDOWN)
        return

    await state.update_data(
        post_text=text,
        post_text_entities=message.entities or []
    )
    await admin_finalize_post(message, bot, state)


async def admin_finalize_post(message: Message, bot: Bot, state: FSMContext) -> None:
    """Kanalga bitta post qilib joylash + tugma"""
    data = await state.get_data()
    kind = data.get("post_kind")
    file_id = data.get("post_file_id")
    text = (data.get("post_text") or "").strip()
    songname = (data.get("post_songname") or "").strip()
    
    caption_entities = None
    if data.get("post_text_entities_prefill") is not None and data.get("post_text_prefill"):
        caption_entities = data.get("post_text_entities_prefill") or []
    elif data.get("post_text_entities") is not None and text:
        caption_entities = data.get("post_text_entities") or []

    if not kind or not file_id:
        await message.answer("❌ *Post ma'lumoti topilmadi. /post ni qayta bosing.*", parse_mode=ParseMode.MARKDOWN)
        await state.clear()
        return

    title_line = songname if songname else "Audio"

    # Generate unique ID
    audio_id = str(uuid.uuid4())[:8]

    # Save to storage
    storage = load_audio_storage()
    storage[audio_id] = {
        "file_id": file_id,
        "title": title_line,
    }
    save_audio_storage(storage)

    me = await bot.get_me()
    bot_link = f"https://t.me/{me.username}?start={audio_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Profilga qo'yish", url=bot_link)]])

    try:
        if kind == "voice":
            await bot.send_voice(
                chat_id=CHANNEL_ID,
                voice=file_id,
                caption=text if text else None,
                caption_entities=caption_entities if caption_entities else None,
                reply_markup=kb,
            )
        else:
            await bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=file_id,
                caption=text if text else None,
                caption_entities=caption_entities if caption_entities else None,
                reply_markup=kb,
            )

        await message.answer(f"✅ *Kanalga joylandi!*  ID: `{audio_id}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.answer(f"❌ Kanalga yuborishda xato: {str(e)[:120]}")
    finally:
        await state.clear()


@router.message(Command("forceset", "force_set"))
async def force_set_command(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        await message.answer(
            "Foydalanish: `/forceset @kanal` (max 5 ta)\n"
            "Ko'rish: `/stats`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    ok, msg = add_force_channel(args[0])
    channels = load_force_channels()
    cur_text = ", ".join(channels) if channels else "Yo'q"
    warn = ""
    if ok:
        try:
            await bot.get_chat(_normalize_channel_ref(args[0]))
        except Exception:
            warn = "\n\n⚠️ *Diqqat:* bot bu kanalni ko'ra olmayapti. Kanalda bot admin bo'lishi kerak, aks holda majburiy tekshiruv ishlamaydi."
    await message.answer(
        ("✅ " if ok else "❌ ") + f"*{msg}*\n\nHozirgi: `{cur_text}`{warn}",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("forceclear", "force_clear"))
async def force_clear_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if args:
        ref = args[0]
        ok, msg = remove_force_channel(ref)
        channels = load_force_channels()
        cur_text = ", ".join(channels) if channels else "Yo'q"
        await message.answer(
            ("✅ " if ok else "❌ ") + f"*{msg}*\n\nHozirgi: `{cur_text}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    channels = load_force_channels()
    if not channels:
        await message.answer("Majburiy kanal yo'q.", parse_mode=ParseMode.MARKDOWN)
        return

    rows = [[InlineKeyboardButton(text=f"🗑 {ch}", callback_data=f"rmch:{ch}")] for ch in channels]
    rows.append([InlineKeyboardButton(text="🗑 Hammasini o'chirish", callback_data="rmch:all")])
    await message.answer(
        "Qaysi kanalni o'chiramiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("stats"))
async def stats_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    storage = load_audio_storage()
    force_list = load_force_channels()
    force_ch = ", ".join(force_list) if force_list else "Yo'q"
    users_count = get_users_count()
    
    await message.answer(
        f"📊 *Statistika*\n\n"
        f"👥 Foydalanuvchilar: *{users_count}* ta\n"
        f"🎵 Audiolar: *{len(storage)}* ta\n"
        f"📢 Majburiy kanal: `{force_ch}`",
        parse_mode=ParseMode.MARKDOWN
    )


# ============== SENTAL (BROADCAST) ==============
@router.message(Command("sental"))
async def sental_command(message: Message, state: FSMContext):
    """Barchaga xabar yuborish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    users_count = get_users_count()
    await message.answer(
        f"📨 *Sental (Broadcast)*\n\n"
        f"👥 Bazada *{users_count}* ta foydalanuvchi bor.\n\n"
        "Xabar yuboring (matn, rasm, video, audio — nima bo'lsa ham).\n"
        "Qanday yuborsangiz, shunday ketadi.\n\n"
        "Bekor qilish: /cancel",
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(AdminSentalStates.waiting_message)


@router.message(AdminSentalStates.waiting_message)
async def sental_receive_message(message: Message, bot: Bot, state: FSMContext):
    """Sental uchun xabar qabul qilish va yuborish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    user_ids = get_all_user_ids()
    if not user_ids:
        await message.answer("❌ Bazada foydalanuvchilar yo'q.")
        return
    
    # Progress xabar
    progress_msg = await message.answer(
        f"📨 *Yuborilmoqda...*\n\n"
        f"Jami: {len(user_ids)} ta",
        parse_mode=ParseMode.MARKDOWN
    )
    
    success = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            # Xabarni copy qilish (qanday kelsa shunday ketadi)
            await message.copy_to(chat_id=user_id)
            success += 1
        except Exception as e:
            failed += 1
            # User blocked bot or deleted account
            print(f"Sental error for {user_id}: {e}")
        
        # Telegram limit: 30 xabar/sekund
        if (success + failed) % 25 == 0:
            await asyncio.sleep(1)
            # Progress yangilash
            try:
                await progress_msg.edit_text(
                    f"📨 *Yuborilmoqda...*\n\n"
                    f"✅ Yuborildi: {success}\n"
                    f"❌ Xato: {failed}\n"
                    f"📊 Jami: {len(user_ids)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    # Natija
    try:
        await progress_msg.edit_text(
            f"✅ *Sental yakunlandi!*\n\n"
            f"📨 Yuborildi: *{success}* ta\n"
            f"❌ Xato: *{failed}* ta\n"
            f"📊 Jami: *{len(user_ids)}* ta",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await message.answer(
            f"✅ *Sental yakunlandi!*\n\n"
            f"📨 Yuborildi: *{success}* ta\n"
            f"❌ Xato: *{failed}* ta\n"
            f"📊 Jami: *{len(user_ids)}* ta",
            parse_mode=ParseMode.MARKDOWN
        )


# ============== CALLBACK HANDLERS ==============
@router.callback_query(F.data.startswith("chkjoin:"))
async def callback_check_join(callback: CallbackQuery, bot: Bot):
    """User clicks 'Tekshirish' after joining."""
    await callback.answer()

    user_id = callback.from_user.id
    data = callback.data or ""
    _, audio_id = data.split(":", 1)

    # General check from /start screen
    if audio_id == "start":
        if not await check_force_subscribe(user_id, bot):
            kb = build_force_join_keyboard()
            try:
                await callback.message.answer(
                    "⚠️ Hali obuna bo'lmagansiz. Iltimos, kanallarga obuna bo'ling va yana tekshiring.",
                    reply_markup=kb,
                )
            except Exception:
                pass
            return

        await callback.message.answer(
            "✅ Obuna tasdiqlandi!\n\n🎵 Endi voice yuboring.",
        )
        return

    if not await check_force_subscribe(user_id, bot):
        kb = build_force_join_keyboard(pending_audio_id=audio_id)
        try:
            await callback.message.answer(
                "⚠️ Hali obuna bo'lmagansiz. Iltimos, kanallarga obuna bo'ling va qayta bosing.",
                reply_markup=kb,
            )
        except Exception:
            pass
        return

    storage = load_audio_storage()
    if audio_id not in storage:
        await callback.message.answer("❌ Audio topilmadi. Kanal tugmasini yana bosing.")
        return
    audio_data = storage[audio_id]
    file_id = audio_data.get("file_id")
    title = audio_data.get("title", "")
    await send_with_progress(callback.message, bot, file_id, title)


@router.callback_query(F.data.startswith("rmch:"))
async def callback_remove_channel(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    _, ref = (callback.data or "").split(":", 1)
    ok, msg = remove_force_channel(ref)
    channels = load_force_channels()
    cur_text = ", ".join(channels) if channels else "Yo'q"
    try:
        await callback.message.edit_text(
            ("✅ " if ok else "❌ ") + f"{msg}\n\nHozirgi: `{cur_text}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await callback.message.answer(
            ("✅ " if ok else "❌ ") + f"{msg}\n\nHozirgi: `{cur_text}`",
            parse_mode=ParseMode.MARKDOWN,
        )


# ============== MAIN ==============
async def on_startup(bot: Bot):
    """Bot ishga tushganda"""
    logger.info("Bot starting up...")
    try:
        me = await bot.get_me()
        logger.info(f"Bot started: @{me.username} (ID: {me.id})")
        
        # DATA_DIR tekshirish
        if os.path.exists(DATA_DIR):
            logger.info(f"DATA_DIR exists: {DATA_DIR}")
            # Fayllarni tekshirish
            for fname in [AUDIO_STORAGE_FILE, FORCE_CHANNELS_FILE, USERS_FILE]:
                exists = "✓" if os.path.exists(fname) else "✗"
                logger.info(f"  {exists} {fname}")
        else:
            logger.warning(f"DATA_DIR does not exist: {DATA_DIR}")
    except Exception as e:
        logger.error(f"Startup error: {e}")


async def main():
    try:
        bot = Bot(token=TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        
        # Startup handler
        dp.startup.register(on_startup)
        
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
