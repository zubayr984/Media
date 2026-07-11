import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Bot tokeningizni bu yerga kiriting (BotFather dan oling)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# TERMUX uchun qo'shimcha sozlamalar
import sys
import logging
logging.basicConfig(level=logging.INFO)

# Bu funksiya endi kerak emas, o'chirildi

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
    
    # URL tekshirish
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Iltimos, to'g'ri link yuboring!")
        return
    
    # Yuklanayotgani haqida xabar
    status_message = await update.message.reply_text("⏳ Yuklab olinmoqda...")
    
    try:
        # Vaqtinchalik fayl nomi
        output_file = f"downloads/{update.message.chat_id}_{update.message.message_id}.%(ext)s"
        os.makedirs("downloads", exist_ok=True)
        
        # yt-dlp sozlamalari - FFmpeg kerak emas
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Bitta eng yaxshi formatni tanlash
            'outtmpl': output_file,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_color': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ma'lumot olish
            info = ydl.extract_info(url, download=True)
            
            if info is None:
                await status_message.edit_text("❌ Video ma'lumotlarini olishda xatolik!")
                return
                
            filename = ydl.prepare_filename(info)
            
            # Fayl mavjudligini tekshirish
            if not os.path.exists(filename):
                await status_message.edit_text("❌ Fayl yuklanmadi!")
                return
            
            # Fayl turini aniqlash
            file_ext = filename.split('.')[-1].lower()
            file_size = os.path.getsize(filename)
            title = info.get('title', 'Media')[:1000]
            
            await status_message.edit_text("📤 Yuborilmoqda...")
            
            # Faylni yuborish
            with open(filename, 'rb') as file:
                # Rasm
                if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    await update.message.reply_photo(
                        photo=file,
                        caption=f"✅ {title}"
                    )
                
                # Video
                elif file_ext in ['mp4', 'mkv', 'avi', 'mov', 'webm', 'm4v']:
                    # Agar 50MB dan katta bo'lsa
                    if file_size > 50 * 1024 * 1024:
                        await status_message.edit_text("⚠️ Fayl hajmi katta (50MB+), biroz kutish kerak...")
                        await update.message.reply_document(
                            document=file,
                            caption=f"✅ {title}\n\n📦 Hajm: {file_size / (1024*1024):.1f} MB",
                            filename=f"{title[:50]}.{file_ext}"
                        )
                    else:
                        # Video sifatida yuborish
                        duration = info.get('duration', 0)
                        width = info.get('width', 640)
                        height = info.get('height', 360)
                        
                        await update.message.reply_video(
                            video=file,
                            duration=int(duration) if duration else None,
                            width=width,
                            height=height,
                            caption=f"✅ {title}",
                            supports_streaming=True,
                            filename=f"{title[:50]}.{file_ext}"
                        )
                
                # Audio
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
                
                # Boshqa formatlar
                else:
                    await update.message.reply_document(
                        document=file,
                        caption=f"✅ {title}",
                        filename=f"{title[:50]}.{file_ext}"
                    )
            
            # Vaqtinchalik faylni o'chirish
            try:
                os.remove(filename)
            except:
                pass
                
            await status_message.delete()
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'ffmpeg' in error_msg.lower():
            await status_message.edit_text(
                "❌ Video yuklab olish xatosi!\n\n"
                "💡 Muammo: Ba'zi videolar murakkab formatda.\n"
                "Iltimos, boshqa link yuboring yoki botni serverda ishga tushiring."
            )
        else:
            await status_message.edit_text(
                f"❌ Yuklab olishda xatolik:\n\n"
                f"Bu link:\n"
                f"• Privat bo'lishi mumkin\n"
                f"• Noto'g'ri link\n"
                f"• Qo'llab-quvvatlanmaydigan sayt"
            )
    except Exception as e:
        await status_message.edit_text(
            f"❌ Kutilmagan xatolik!\n\n"
            f"Iltimos, boshqa link bilan sinab ko'ring."
        )
    finally:
        # Barcha qoldiq fayllarni tozalash
        try:
            for file in os.listdir("downloads"):
                if file.startswith(f"{update.message.chat_id}_{update.message.message_id}"):
                    try:
                        os.remove(os.path.join("downloads", file))
                    except:
                        pass
        except:
            pass

def main():
    """Botni ishga tushirish"""
    print("🤖 Bot ishga tushmoqda...")
    
    # Application yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Komandalar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Link handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        download_media
    ))
    
    # Botni ishga tushirish
    print("✅ Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
