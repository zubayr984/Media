import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Railway'da Variables bo'limidan BOT_TOKEN o'zgaruvchisi orqali olinadi
BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    await update.message.reply_text(
        "🎬 Salom! Men media yuklovchi botman.\n\n"
        "📱 Quyidagi platformalardan link yuboring:\n"
        "• Instagram\n"
        "• YouTube\n"
        "• Facebook\n"
        "• TikTok\n"
        "• Twitter\n"
        "• va boshqalar...\n\n"
        "Men sizga video, rasm yoki audio yuborishim mumkin!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    await update.message.reply_text(
        "📖 Qanday foydalanish:\n\n"
        "1️⃣ Ixtiyoriy ijtimoiy tarmoqdan link nusxa oling\n"
        "2️⃣ Linkni menga yuboring\n"
        "3️⃣ Kutib turing, men sizga media faylni yuboraman!\n\n"
        "⚠️ Ba'zi privatlik sozlamalari bo'lgan postlarni yuklab ololmayman."
    )


async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Media yuklab olish funksiyasi"""
    url = update.message.text.strip()

    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Iltimos, to'g'ri link yuboring!")
        return

    status_message = await update.message.reply_text("⏳ Yuklab olinmoqda...")

    filename = None
    try:
        output_file = f"downloads/{update.message.chat_id}_{update.message.message_id}.%(ext)s"
        os.makedirs("downloads", exist_ok=True)

        # Railway'da ffmpeg o'rnatilgan (nixpacks.toml orqali), shuning uchun
        # eng yaxshi video+audio formatlarni birlashtirib olamiz
        ydl_opts = {
            'format': 'best',  # Bitta tayyor faylni tanlaydi, ffmpeg kerak emas
            'outtmpl': output_file,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_color': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/120.0.0.0 Safari/537.36'
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if info is None:
                await status_message.edit_text("❌ Video ma'lumotlarini olishda xatolik!")
                return

            filename = ydl.prepare_filename(info)

            # merge bo'lganda kengaytma mp4 ga o'zgarishi mumkin
            if info.get('requested_downloads'):
                filename = info['requested_downloads'][0].get('filepath', filename)

            if not os.path.exists(filename):
                # mp4 variantini tekshirish
                base = os.path.splitext(filename)[0]
                if os.path.exists(base + ".mp4"):
                    filename = base + ".mp4"
                else:
                    await status_message.edit_text("❌ Fayl yuklanmadi!")
                    return

            file_ext = filename.split('.')[-1].lower()
            file_size = os.path.getsize(filename)
            title = info.get('title', 'Media')[:1000]

            await status_message.edit_text("📤 Yuborilmoqda...")

            with open(filename, 'rb') as file:
                if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    await update.message.reply_photo(
                        photo=file,
                        caption=f"✅ {title}"
                    )

                elif file_ext in ['mp4', 'mkv', 'avi', 'mov', 'webm', 'm4v']:
                    if file_size > 50 * 1024 * 1024:
                        await status_message.edit_text("⚠️ Fayl hajmi katta (50MB+), yuborilmoqda...")
                        await update.message.reply_document(
                            document=file,
                            caption=f"✅ {title}\n\n📦 Hajm: {file_size / (1024*1024):.1f} MB",
                            filename=f"{title[:50]}.{file_ext}"
                        )
                    else:
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

                elif file_ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                    duration = info.get('duration', 0)
                    performer = info.get('uploader', 'Unknown')

                    await update.message.reply_audio(
                        audio=file,
                        duration=int(duration) if duration else None,
                        performer=performer,
                        title=title,
                        caption=f"✅ {title}"
                    )

                else:
                    await update.message.reply_document(
                        document=file,
                        caption=f"✅ {title}",
                        filename=f"{title[:50]}.{file_ext}"
                    )

            await status_message.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        error_text = str(e)
        # Foydalanuvchiga aniq sabab ko'rsatiladi (tuzatish uchun muhim)
        await status_message.edit_text(
            f"❌ Yuklab olishda xatolik:\n\n{error_text[:600]}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_message.edit_text(
            f"❌ Kutilmagan xatolik:\n\n{str(e)[:600]}"
        )
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


def main():
    """Botni ishga tushirish"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! Railway Variables bo'limiga qo'shing.")
        return

    logger.info("🤖 Bot ishga tushmoqda...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        download_media
    ))

    logger.info("✅ Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
