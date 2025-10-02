import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)

# توکن ربات - این رو بعداً در Render تنظیم می‌کنیم
BOT_TOKEN = os.environ.get('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 سلام {user.mention_html()}!\n\n"
        "🤖 ربات Aternos با موفقیت راه‌اندازی شد!\n\n"
        "🔧 دستورات:\n"
        "/start - راهنما\n"
        "/status - وضعیت\n"
        "به زودی قابلیت کنترل سرور اضافه می‌شود! 🚀"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ ربات فعال است! به زودی قابلیت کنترل سرور اضافه می‌شود.")

def main():
    # ساخت ربات
    application = Application.builder().token(BOT_TOKEN).build()
    
    # دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    
    # اجرا
    print("🤖 ربات در حال راه‌اندازی...")
    application.run_polling()

if __name__ == '__main__':
    main()