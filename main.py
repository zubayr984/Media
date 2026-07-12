import os
import time
import sqlite3
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# ================== SOZLAMALAR ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Admin Telegram ID'lari, vergul bilan ajratilgan: "123456789,987654321"
ADMIN_IDS = set(
    int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()
)

# YouTube uchun cookie (ixtiyoriy)
COOKIES_FILE = "cookies.txt"
_cookies_env = os.environ.get("COOKIES_TXT")
if _cookies_env:
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(_cookies_env)

RATE_LIMIT_SECONDS = 8  # bir foydalanuvchi ketma-ket so'rov yuborishi orasidagi minimal vaqt

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

_last_request = {}  # user_id -> oxirgi so'rov vaqti (rate limit uchun)

# ================== MA'LUMOTLAR BAZASI ==================
DB_FILE = "bot.db"


def db_init():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        joined_at TEXT,
        banned INTEGER DEFAULT 0,
        download_count INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        url TEXT,
        title TEXT,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()


def db_register_user(user_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if c.fetchone() is None:
        c.execute(
            "INSERT INTO users (user_id, username, joined_at) VALUES (?, ?, ?)",
            (user_id, username, datetime.now().isoformat())
        )
        conn.commit()
    conn.close()


def db_is_banned(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])


def db_set_ban(user_id, banned: bool):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET banned=? WHERE user_id=?", (1 if banned else 0, user_id))
    conn.commit()
    changed = c.rowcount > 0
    conn.close()
    return changed


def db_add_history(user_id, url, title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO history (user_id, url, title, created_at) VALUES (?, ?, ?, ?)",
        (user_id, url, title, datetime.now().isoformat())
    )
    c.execute("UPDATE users SET download_count = download_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def db_get_history(user_id, limit=5):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT title, url, created_at FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def db_get_user_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT joined_at, download_count FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def db_get_global_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned=1")
    banned_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM history")
    total_downloads = c.fetchone()[0]
    conn.close()
    return total_users, banned_users, total_downloads


def db_get_all_user_ids():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE banned=0")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


# ================== YORDAMCHI FUNKSIYALAR ==================

def is_admin(user_id):
    return user_id in ADMIN_IDS


def check_rate_limit(user_id):
    """True qaytarsa - ruxsat bor. False - hali kutish kerak."""
    now = time.time()
    last = _last_request.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return False
    _last_request[user_id] = now
    return True


# ================== KOMANDALAR ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_register_user(user.id, user.username or user.first_name)

    await update.message.reply_text(
        "🎬 Salom! Men media yuklovchi botman.\n\n"
        "📱 Quyidagi platformalardan link yuboring:\n"
        "• Instagram\n"
        "• YouTube\n"
        "• Facebook\n"
        "• TikTok\n"
        "• Twitter\n"
        "• va boshqalar...\n\n"
        "Men sizga video, rasm yoki audio yuborishim mumkin!\n\n"
        "Barcha buyruqlar uchun /help yozing."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        "📖 <b>Botdan foydalanish qo'llanmasi</b>\n\n"
        "<b>Asosiy buyruqlar:</b>\n"
        "/start — botni ishga tushirish\n"
        "/help — shu yordam matni\n"
        "/mp3 &lt;link&gt; — linkdan faqat audio (mp3) ajratib olish\n"
        "/mystats — shaxsiy statistikangiz\n"
        "/history — oxirgi 5 ta yuklagan faylingiz\n\n"
        "<b>Qanday ishlatiladi:</b>\n"
        "1️⃣ Istalgan ijtimoiy tarmoqdan link nusxa oling\n"
        "2️⃣ Linkni to'g'ridan-to'g'ri menga yuboring\n"
        "3️⃣ Video/rasm/audio faylni oling!\n\n"
        f"⏱ Har bir so'rov orasida {RATE_LIMIT_SECONDS} soniya kutish kerak (spamdan himoya).\n"
        "⚠️ Fayl 50MB dan katta bo'lsa, Telegram cheklovi sabab yubora olmayman."
    )

    if is_admin(user.id):
        text += (
            "\n\n👑 <b>Admin buyruqlari:</b>\n"
            "/stats — botning umumiy statistikasi\n"
            "/users — ro'yxatdan o'tgan foydalanuvchilar soni\n"
            "/ban &lt;user_id&gt; — foydalanuvchini bloklash\n"
            "/unban &lt;user_id&gt; — blokdan chiqarish\n"
            "/broadcast &lt;matn&gt; — barcha foydalanuvchilarga xabar yuborish"
        )

    await update.message.reply_text(text, parse_mode="HTML")


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    row = db_get_user_stats(user.id)
    if not row:
        await update.message.reply_text("Siz haqingizda ma'lumot topilmadi. /start bosing.")
        return
    joined_at, count = row
    joined_date = joined_at.split("T")[0]
    await update.message.reply_text(
        f"📊 <b>Sizning statistikangiz</b>\n\n"
        f"📅 Ro'yxatdan o'tgan sana: {joined_date}\n"
        f"⬇️ Yuklagan fayllar soni: {count}",
        parse_mode="HTML"
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rows = db_get_history(user.id, limit=5)
    if not rows:
        await update.message.reply_text("📭 Hali hech narsa yuklamagansiz.")
        return

    text = "🕒 <b>Oxirgi yuklamalaringiz:</b>\n\n"
    for title, url, created_at in rows:
        date = created_at.split("T")[0]
        text += f"• {title[:50]}\n  {date}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ---------- ADMIN BUYRUQLARI ----------

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    total_users, banned_users, total_downloads = db_get_global_stats()
    await update.message.reply_text(
        f"📈 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total_users}\n"
        f"🚫 Bloklanganlar: {banned_users}\n"
        f"⬇️ Jami yuklamalar: {total_downloads}",
        parse_mode="HTML"
    )


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    total_users, banned_users, _ = db_get_global_stats()
    await update.message.reply_text(
        f"👥 Ro'yxatdan o'tganlar: {total_users}\n🚫 Bloklanganlar: {banned_users}"
    )


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /ban <user_id>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id butun son bo'lishi kerak.")
        return

    if db_set_ban(target_id, True):
        await update.message.reply_text(f"🚫 {target_id} bloklandi.")
    else:
        await update.message.reply_text("❌ Bunday foydalanuvchi topilmadi.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /unban <user_id>")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id butun son bo'lishi kerak.")
        return

    if db_set_ban(target_id, False):
        await update.message.reply_text(f"✅ {target_id} blokdan chiqarildi.")
    else:
        await update.message.reply_text("❌ Bunday foydalanuvchi topilmadi.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return
    if not context.args:
        await update.message.reply_text("Foydalanish: /broadcast <xabar matni>")
        return

    text = "📢 " + " ".join(context.args)
    user_ids = db_get_all_user_ids()
    sent, failed = 0, 0

    status = await update.message.reply_text(f"⏳ {len(user_ids)} foydalanuvchiga yuborilmoqda...")

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Exception:
            failed += 1

    await status.edit_text(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")


# ================== YUKLAB OLISH LOGIKASI ==================

async def _perform_download(update: Update, url: str, audio_only: bool = False):
    status_message = await update.message.reply_text("⏳ Yuklab olinmoqda...")
    filename = None
    user = update.effective_user

    try:
        output_file = f"downloads/{update.message.chat_id}_{update.message.message_id}.%(ext)s"
        os.makedirs("downloads", exist_ok=True)

        if audio_only:
            base_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_file,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'no_color': True,
            }
        else:
            base_opts = {
                'format': 'best[filesize<50M]/best',
                'outtmpl': output_file,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'no_color': True,
            }

        base_opts['http_headers'] = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36'
        }

        # YouTube uchun: 'android'/'ios' klient ba'zan cookie'siz ham
        # bot-tekshiruvini chetlab o'tadi
        base_opts['extractor_args'] = {
            'youtube': {'player_client': ['android', 'web']}
        }

        # Bir nechta urinish strategiyasi: avval cookie'siz, keyin cookie bilan
        attempts = [dict(base_opts)]
        if os.path.exists(COOKIES_FILE):
            with_cookies = dict(base_opts)
            with_cookies['cookiefile'] = COOKIES_FILE
            attempts.append(with_cookies)

        info = None
        last_error = None
        for opts in attempts:
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                if info is not None:
                    break
            except yt_dlp.utils.DownloadError as e:
                last_error = e
                continue

        if info is None:
            if last_error:
                raise last_error
            await status_message.edit_text("❌ Video ma'lumotlarini olishda xatolik!")
            return

        with yt_dlp.YoutubeDL(base_opts) as ydl:
            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                await status_message.edit_text("❌ Fayl yuklanmadi!")
                return

            file_ext = filename.split('.')[-1].lower()
            file_size = os.path.getsize(filename)
            title = info.get('title', 'Media')[:1000]

            await status_message.edit_text("📤 Yuborilmoqda...")

            with open(filename, 'rb') as file:
                if audio_only or file_ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                    duration = info.get('duration', 0)
                    performer = info.get('uploader', 'Unknown')
                    await update.message.reply_audio(
                        audio=file,
                        duration=int(duration) if duration else None,
                        performer=performer,
                        title=title,
                        caption=f"✅ {title}"
                    )

                elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    await update.message.reply_photo(photo=file, caption=f"✅ {title}")

                elif file_ext in ['mp4', 'mkv', 'avi', 'mov', 'webm', 'm4v']:
                    if file_size > 49 * 1024 * 1024:
                        await status_message.edit_text(
                            f"❌ Fayl juda katta ({file_size / (1024*1024):.1f} MB).\n\n"
                            "Telegram bot orqali maksimum 50MB fayl yuborish mumkin."
                        )
                        return
                    duration = info.get('duration', 0)
                    width = info.get('width', 640) or 640
                    height = info.get('height', 360) or 360
                    await update.message.reply_video(
                        video=file,
                        duration=int(duration) if duration else None,
                        width=width,
                        height=height,
                        caption=f"✅ {title}",
                        supports_streaming=True,
                        filename=f"{title[:50]}.{file_ext}"
                    )

                else:
                    await update.message.reply_document(
                        document=file,
                        caption=f"✅ {title}",
                        filename=f"{title[:50]}.{file_ext}"
                    )

            db_add_history(user.id, url, title)
            await status_message.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        await status_message.edit_text(f"❌ Yuklab olishda xatolik:\n\n{str(e)[:600]}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_message.edit_text(f"❌ Kutilmagan xatolik:\n\n{str(e)[:600]}")
    finally:
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
            for f in os.listdir("downloads"):
                if f.startswith(f"{update.message.chat_id}_{update.message.message_id}"):
                    try:
                        os.remove(os.path.join("downloads", f))
                    except:
                        pass
        except:
            pass


async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oddiy link yuborilganda ishlaydi (video/rasm rejimi)"""
    user = update.effective_user
    db_register_user(user.id, user.username or user.first_name)

    if db_is_banned(user.id):
        await update.message.reply_text("🚫 Siz botdan foydalanishdan bloklangansiz.")
        return

    if not check_rate_limit(user.id):
        await update.message.reply_text(
            f"⏳ Iltimos, {RATE_LIMIT_SECONDS} soniyada bir marta so'rov yuboring."
        )
        return

    url = update.message.text.strip()
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Iltimos, to'g'ri link yuboring!")
        return

    await _perform_download(update, url, audio_only=False)


async def mp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mp3 <link> — faqat audio ajratib beradi"""
    user = update.effective_user
    db_register_user(user.id, user.username or user.first_name)

    if db_is_banned(user.id):
        await update.message.reply_text("🚫 Siz botdan foydalanishdan bloklangansiz.")
        return

    if not check_rate_limit(user.id):
        await update.message.reply_text(
            f"⏳ Iltimos, {RATE_LIMIT_SECONDS} soniyada bir marta so'rov yuboring."
        )
        return

    if not context.args:
        await update.message.reply_text("Foydalanish: /mp3 <link>")
        return

    url = context.args[0].strip()
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Iltimos, to'g'ri link yuboring!")
        return

    await _perform_download(update, url, audio_only=True)


# ================== ASOSIY FUNKSIYA ==================

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! Railway Variables bo'limiga qo'shing.")
        return

    db_init()
    logger.info("🤖 Bot ishga tushmoqda...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("mp3", mp3_command))

    # Admin buyruqlari
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))

    # Oddiy link yuborilganda
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))

    logger.info("✅ Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
