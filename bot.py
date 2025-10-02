import os
import logging
from datetime import datetime, timedelta
import random
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# گرفتن توکن از متغیر محیطی
TOKEN = os.getenv('8026391620:AAGsQTUZYbCFcvhrLVaUihcGFmsTZA52mHY')
if not TOKEN:
    logging.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
    exit(1)

# دیتابیس در حافظه
users_db = {}
spam_tracker = {}
user_penalties = {}

# داده‌های کشورها و رهبران واقعی
REAL_COUNTRIES = [
    {"code": "US", "name": "ایالات متحده آمریکا", "nuclear_advantage": True, "base_economy": 2000, "base_military": 200},
    {"code": "RU", "name": "روسیه", "nuclear_advantage": True, "base_economy": 1800, "base_military": 220},
    {"code": "CN", "name": "چین", "nuclear_advantage": True, "base_economy": 1900, "base_military": 180},
    {"code": "IR", "name": "ایران", "nuclear_advantage": False, "base_economy": 1100, "base_military": 90},
    {"code": "DE", "name": "آلمان", "nuclear_advantage": False, "base_economy": 1700, "base_military": 120},
    {"code": "JP", "name": "ژاپن", "nuclear_advantage": False, "base_economy": 1600, "base_military": 110},
]

REAL_LEADERS = [
    {"id": 1, "name": "جو بایدن", "country_code": "US", "power": 0.9, "type": "سیاستمدار", "special_ability": "ناتو", "description": "رهبر بلوک غرب"},
    {"id": 2, "name": "ولادیمیر پوتین", "country_code": "RU", "power": 0.95, "type": "استراتژیست", "special_ability": "گاز", "description": "تأثیرگذار در انرژی اروپا"},
    {"id": 3, "name": "شی جین پینگ", "country_code": "CN", "power": 0.92, "type": "اقتصاددان", "special_ability": "راه ابریشم", "description": "رهبری رشد اقتصادی"},
    {"id": 4, "name": "سید ابراهیم رئیسی", "country_code": "IR", "power": 0.8, "type": "سیاستمدار", "special_ability": "مقاومت", "description": "دیپلماسی منطقه‌ای"},
]

class User:
    def __init__(self, user_id: int, username: str = ""):
        self.user_id = user_id
        self.username = username
        self.assign_real_country_and_leader()
        self.economy = self.base_economy
        self.military_power = self.base_military
        self.technology = 50
        self.influence = 0
        self.resources = {
            "gold": 500,
            "oil": 300,
            "uranium": 10 if self.nuclear_advantage else 0
        }
        self.allies = []
        self.nuclear_research_progress = 10 if self.nuclear_advantage else 0
        self.created_at = datetime.now()
        self.last_economic_update = datetime.now()
    
    def assign_real_country_and_leader(self):
        weights = [1.0 / (country["base_economy"] * 0.001) for country in REAL_COUNTRIES]
        country = random.choices(REAL_COUNTRIES, weights=weights)[0]
        
        self.country_code = country["code"]
        self.country_name = country["name"]
        self.nuclear_advantage = country["nuclear_advantage"]
        self.base_economy = country["base_economy"]
        self.base_military = country["base_military"]
        
        country_leaders = [l for l in REAL_LEADERS if l["country_code"] == self.country_code]
        if country_leaders:
            self.leader = random.choice(country_leaders)
        else:
            self.leader = {
                "name": "رهبر ملی",
                "type": "سیاستمدار", 
                "special_ability": "رهبری عمومی",
                "description": "رهبر کشور شما",
                "power": 0.7
            }
    
    def calculate_total_score(self):
        return (self.economy + self.military_power + self.technology + self.influence)
    
    def update_economy(self):
        now = datetime.now()
        if (now - self.last_economic_update).total_seconds() >= 3600:
            growth_rate = random.uniform(0.01, 0.05)
            self.economy *= (1 + growth_rate)
            self.last_economic_update = now

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "ناشناس"
    
    if user_id not in users_db:
        user = User(user_id, username)
        users_db[user_id] = user
        welcome_message = f"""
🏛️ **به GeoPolitix خوش آمدید!**

🏴 کشور شما: **{user.country_name}**
👑 رهبر شما: **{user.leader['name']}**
💪 قدرت رهبر: {user.leader['power'] * 100}%

💰 اقتصاد: **{user.economy:,.0f}**
⚔️ قدرت نظامی: **{user.military_power:,.0f}**
🔬 تکنولوژی: **{user.technology}**

💡 دستورات:
/profile - پروفایل
/leaderboard - جدول رتبه بندی
/allies - مدیریت متحدان
        """
    else:
        user = users_db[user_id]
        welcome_message = f"خوش آمدید بازگشت! 🇮🇷\nکشور شما: {user.country_name}"
    
    await update.message.reply_text(welcome_message)

# دستور /profile
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users_db:
        await update.message.reply_text("❌ شما هنوز ثبت نام نکرده‌اید! /start")
        return
    
    user = users_db[user_id]
    user.update_economy()
    
    profile_text = f"""
🏴 **پروفایل {user.country_name}**

👑 رهبر: {user.leader['name']}
💪 قدرت: {user.leader['power'] * 100}%
🎯 تخصص: {user.leader['type']}

💰 اقتصاد: {user.economy:,.0f}
⚔️ قدرت نظامی: {user.military_power:,.0f}
🔬 تکنولوژی: {user.technology:,.0f}
🌟 نفوذ: {user.influence:,.0f}

{'☢️ دارای مزیت هسته‌ای' if user.nuclear_advantage else '🔒 بدون تسلیحات هسته‌ای'}
🔗 متحدان: {len(user.allies)} کشور
    """
    
    await update.message.reply_text(profile_text)

# سیستم لیدربرد
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏦 اقتصاد", callback_data="leaderboard_economy")],
        [InlineKeyboardButton("⚔️ قدرت نظامی", callback_data="leaderboard_military")],
        [InlineKeyboardButton("🔬 تکنولوژی", callback_data="leaderboard_technology")],
        [InlineKeyboardButton("🏆 امتیاز کلی", callback_data="leaderboard_total")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 **جدول رتبه‌بندی جهانی**\n\nلطفاً معیار رتبه‌بندی را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def handle_leaderboard_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("leaderboard_", "")
    
    for user in users_db.values():
        user.update_economy()
    
    if category == "economy":
        sorted_users = sorted(users_db.values(), key=lambda x: x.economy, reverse=True)
        title = "🏦 10 کشور برتر از نظر اقتصاد"
        field = "اقتصاد"
    elif category == "military":
        sorted_users = sorted(users_db.values(), key=lambda x: x.military_power, reverse=True)
        title = "⚔️ 10 کشور برتر از نظر قدرت نظامی"
        field = "قدرت نظامی"
    elif category == "technology":
        sorted_users = sorted(users_db.values(), key=lambda x: x.technology, reverse=True)
        title = "🔬 10 کشور برتر از نظر تکنولوژی"
        field = "تکنولوژی"
    else:
        sorted_users = sorted(users_db.values(), key=lambda x: x.calculate_total_score(), reverse=True)
        title = "🏆 10 کشور برتر از نظر امتیاز کلی"
        field = "امتیاز کلی"
    
    leaderboard_text = f"**{title}**\n\n"
    
    for i, user in enumerate(sorted_users[:10], 1):
        if category == "economy":
            value = user.economy
        elif category == "military":
            value = user.military_power
        elif category == "technology":
            value = user.technology
        else:
            value = user.calculate_total_score()
        
        leaderboard_text += f"{i}️⃣ **{user.country_name}**\n"
        leaderboard_text += f"   👤 {user.username}\n"
        leaderboard_text += f"   📊 {field}: {value:,.0f}\n\n"
    
    await query.edit_message_text(leaderboard_text)

# سیستم مدیریت اسپم
async def check_spam(user_id: int) -> bool:
    current_time = datetime.now()
    
    if user_id in user_penalties:
        if current_time < user_penalties[user_id]['end_time']:
            return True
        else:
            del user_penalties[user_id]
            if user_id in spam_tracker:
                del spam_tracker[user_id]
    
    if user_id not in spam_tracker:
        spam_tracker[user_id] = {'count': 1, 'first_message_time': current_time}
    else:
        spam_tracker[user_id]['count'] += 1
        
        time_diff = (current_time - spam_tracker[user_id]['first_message_time']).total_seconds()
        if spam_tracker[user_id]['count'] > 5 and time_diff < 30:
            penalty_end = current_time + timedelta(minutes=5)
            user_penalties[user_id] = {'end_time': penalty_end, 'reason': 'اسپم'}
            del spam_tracker[user_id]
            return True
    
    if user_id in spam_tracker:
        time_diff = (current_time - spam_tracker[user_id]['first_message_time']).total_seconds()
        if time_diff > 30:
            spam_tracker[user_id] = {'count': 1, 'first_message_time': current_time}
    
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if await check_spam(user_id):
        if user_id in user_penalties:
            penalty_end = user_penalties[user_id]['end_time']
            await update.message.reply_text(
                f"❌ شما به دلیل اسپم کردن به مدت ۵ دقیقه از دسترسی به ربات محروم شدید.\n"
                f"⏰ محرومیت تا: {penalty_end.strftime('%H:%M')}"
            )
        return
    
    if not update.message.text.startswith('/'):
        await update.message.reply_text(
            "🤖 **GeoPolitix Bot**\n\n"
            "لطفاً از دستورات استفاده کنید:\n"
            "/start - شروع بازی\n"
            "/profile - پروفایل\n"
            "/leaderboard - رتبه‌بندی\n"
            "/help - راهنما"
        )

async def post_init(application: Application):
    # این تابع بعد از راه‌اندازی ربات اجرا می‌شود
    await application.bot.set_webhook(
        f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

def main():
    # ایجاد application
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    
    application.add_handler(CallbackQueryHandler(handle_leaderboard_selection, pattern="^leaderboard_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # شروع ربات
    port = int(os.environ.get('PORT', 8443))
    logging.info(f"🤖 GeoPolitix Bot is starting on port {port}...")
    
    if os.environ.get('RENDER'):
        # روی Render از webhook استفاده می‌کنیم
        logging.info("🚀 Running in production mode with webhook...")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            secret_token=TOKEN,
            webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
        )
    else:
        # روی local از polling استفاده می‌کنیم
        logging.info("🔧 Running in development mode with polling...")
        application.run_polling()

if __name__ == "__main__":
    main()

