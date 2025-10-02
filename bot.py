import logging
from datetime import datetime, timedelta
import random
import json
import telebot
from telebot import types

# تنظیمات اولیه
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# دیتابیس ساده در حافظه
users_db = {}
alliances_db = {}
attacks_queue = {}
spam_tracker = {}
user_penalties = {}

# داده‌های کشورها و رهبران واقعی
REAL_COUNTRIES = [
    {"code": "US", "name": "ایالات متحده آمریکا", "nuclear_advantage": True, "base_economy": 2000, "base_military": 200},
    {"code": "RU", "name": "روسیه", "nuclear_advantage": True, "base_economy": 1800, "base_military": 220},
    {"code": "CN", "name": "چین", "nuclear_advantage": True, "base_economy": 1900, "base_military": 180},
    {"code": "FR", "name": "فرانسه", "nuclear_advantage": True, "base_economy": 1600, "base_military": 150},
    {"code": "GB", "name": "بریتانیا", "nuclear_advantage": True, "base_economy": 1500, "base_military": 140},
    {"code": "IN", "name": "هند", "nuclear_advantage": True, "base_economy": 1400, "base_military": 130},
    {"code": "PK", "name": "پاکستان", "nuclear_advantage": True, "base_economy": 1200, "base_military": 120},
    {"code": "IL", "name": "اسرائیل", "nuclear_advantage": True, "base_economy": 1300, "base_military": 110},
    {"code": "KP", "name": "کره شمالی", "nuclear_advantage": True, "base_economy": 800, "base_military": 100},
    {"code": "IR", "name": "ایران", "nuclear_advantage": False, "base_economy": 1100, "base_military": 90},
    {"code": "DE", "name": "آلمان", "nuclear_advantage": False, "base_economy": 1700, "base_military": 120},
    {"code": "JP", "name": "ژاپن", "nuclear_advantage": False, "base_economy": 1600, "base_military": 110},
    {"code": "SA", "name": "عربستان سعودی", "nuclear_advantage": False, "base_economy": 1300, "base_military": 80},
    {"code": "TR", "name": "ترکیه", "nuclear_advantage": False, "base_economy": 1200, "base_military": 85},
    {"code": "BR", "name": "برزیل", "nuclear_advantage": False, "base_economy": 1400, "base_military": 70},
]

REAL_LEADERS = [
    {"id": 1, "name": "جو بایدن", "country_code": "US", "power": 0.9, "type": "سیاستمدار", "special_ability": "ناتو", "description": "رهبر بلوک غرب"},
    {"id": 2, "name": "ولادیمیر پوتین", "country_code": "RU", "power": 0.95, "type": "استراتژیست", "special_ability": "گاز", "description": "تأثیرگذار در انرژی اروپا"},
    {"id": 3, "name": "شی جین پینگ", "country_code": "CN", "power": 0.92, "type": "اقتصاددان", "special_ability": "راه ابریشم", "description": "رهبری رشد اقتصادی"},
    {"id": 4, "name": "امانوئل مکرون", "country_code": "FR", "power": 0.85, "type": "دیپلمات", "special_ability": "اتحادیه اروپا", "description": "محور اروپای متحد"},
    {"id": 5, "name": "ریشی سوناک", "country_code": "GB", "power": 0.82, "type": "تکنوکرات", "special_ability": "خدمات مالی", "description": "تخصص در اقتصاد دیجیتال"},
    {"id": 6, "name": "نارندرا مودی", "country_code": "IN", "power": 0.88, "type": "انقلابی", "special_ability": "فناوری", "description": "رهبری رشد سریع"},
    {"id": 7, "name": "سید ابراهیم رئیسی", "country_code": "IR", "power": 0.8, "type": "سیاستمدار", "special_ability": "مقاومت", "description": "دیپلماسی منطقه‌ای"},
    {"id": 8, "name": "محمد بن سلمان", "country_code": "SA", "power": 0.78, "type": "اصلاح‌طلب", "special_ability": "نفت", "description": "ویژن ۲۰۳۰"},
    {"id": 9, "name": "رجب طیب اردوغان", "country_code": "TR", "power": 0.83, "type": "استراتژیست", "special_ability": "پل ارتباطی", "description": "موقعیت ژئوپلیتیک"},
    {"id": 10, "name": "بنیامین نتانیاهو", "country_code": "IL", "power": 0.81, "type": "امنیتی", "special_ability": "تکنولوژی", "description": "قدرت سایبری"},
]

# کلاس کاربر
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
        # انتخاب تصادفی کشور با شانس کمتر برای کشورهای قوی
        weights = [1.0 / (country["base_economy"] * 0.001) for country in REAL_COUNTRIES]
        country = random.choices(REAL_COUNTRIES, weights=weights)[0]
        
        self.country_code = country["code"]
        self.country_name = country["name"]
        self.nuclear_advantage = country["nuclear_advantage"]
        self.base_economy = country["base_economy"]
        self.base_military = country["base_military"]
        
        # پیدا کردن رهبر مربوط به کشور
        country_leaders = [l for l in REAL_LEADERS if l["country_code"] == self.country_code]
        if country_leaders:
            self.leader = random.choice(country_leaders)
        else:
            # اگر رهبری پیدا نشد، یک رهبر عمومی
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
        # به روزرسانی خودکار اقتصاد هر 1 ساعت
        now = datetime.now()
        if (now - self.last_economic_update).total_seconds() >= 3600:  # 1 ساعت
            growth_rate = random.uniform(0.01, 0.05)  # رشد 1-5%
            self.economy *= (1 + growth_rate)
            self.last_economic_update = now

# ایجاد ربات
bot = telebot.TeleBot("8026391620:AAGsQTUZYbCFcvhrLVaUihcGFmsTZA52mHY")

# سیستم مدیریت اسپم
def check_spam(user_id: int) -> bool:
    current_time = datetime.now()
    
    if user_id in user_penalties:
        if current_time < user_penalties[user_id]['end_time']:
            return True
        else:
            del user_penalties[user_id]
            if user_id in spam_tracker:
                del spam_tracker[user_id]
    
    if user_id not in spam_tracker:
        spam_tracker[user_id] = {
            'count': 1,
            'first_message_time': current_time
        }
    else:
        spam_tracker[user_id]['count'] += 1
        
        time_diff = (current_time - spam_tracker[user_id]['first_message_time']).total_seconds()
        if spam_tracker[user_id]['count'] > 5 and time_diff < 30:
            penalty_end = current_time + timedelta(minutes=5)
            user_penalties[user_id] = {
                'end_time': penalty_end,
                'reason': 'اسپم'
            }
            del spam_tracker[user_id]
            return True
    
    if user_id in spam_tracker:
        time_diff = (current_time - spam_tracker[user_id]['first_message_time']).total_seconds()
        if time_diff > 30:
            spam_tracker[user_id] = {
                'count': 1,
                'first_message_time': current_time
            }
    
    return False

# دستور /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "ناشناس"
    
    if check_spam(user_id):
        if user_id in user_penalties:
            penalty_end = user_penalties[user_id]['end_time']
            bot.reply_to(message, f"❌ شما به دلیل اسپم کردن به مدت ۵ دقیقه از دسترسی به ربات محروم شدید.\n⏰ محرومیت تا: {penalty_end.strftime('%H:%M')}")
        return
    
    if user_id not in users_db:
        user = User(user_id, username)
        users_db[user_id] = user
        welcome_message = f"""
🏛️ **به GeoPolitix خوش آمدید!**

🏴 کشور شما: **{user.country_name}**
👑 رهبر شما: **{user.leader['name']}**
💪 قدرت رهبر: {user.leader['power'] * 100}%
🎯 تخصص: {user.leader['type']}
✨ توانایی ویژه: {user.leader['special_ability']}

💰 اقتصاد: **{user.economy:,.0f}**
⚔️ قدرت نظامی: **{user.military_power:,.0f}**
🔬 تکنولوژی: **{user.technology}**
{'☢️ مزیت هسته‌ای: دارد' if user.nuclear_advantage else '🔒 بدون تسلیحات هسته‌ای'}

💡 برای شروع از دستورات زیر استفاده کنید:
/attack - حمله به کشور دیگر
/profile - مشاهده پروفایل
/leaderboard - جدول رتبه بندی
/allies - مدیریت متحدان
        """
    else:
        user = users_db[user_id]
        welcome_message = f"""
خوش آمدید بازگشت! 🇮🇷
کشور شما: {user.country_name}
رهبر: {user.leader['name']}
        """
    
    bot.reply_to(message, welcome_message)

# دستور /profile
@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = message.from_user.id
    
    if check_spam(user_id):
        return
    
    user = users_db.get(user_id)
    if not user:
        bot.reply_to(message, "❌ شما هنوز ثبت نام نکرده‌اید! /start")
        return
    
    # به روزرسانی اقتصاد قبل از نمایش
    user.update_economy()
    
    profile_text = f"""
🏴 **پروفایل {user.country_name}**

👑 رهبر: {user.leader['name']}
💪 قدرت: {user.leader['power'] * 100}%
🎯 تخصص: {user.leader['type']}
✨ توانایی: {user.leader['special_ability']}
📝 درباره: {user.leader['description']}

💰 اقتصاد: {user.economy:,.0f}
⚔️ قدرت نظامی: {user.military_power:,.0f}
🔬 تکنولوژی: {user.technology:,.0f}
🌟 نفوذ: {user.influence:,.0f}

💎 منابع:
  • طلا: {user.resources['gold']}
  • نفت: {user.resources['oil']}
  • اورانیوم: {user.resources['uranium']}

{'☢️ **دارای مزیت هسته‌ای**' if user.nuclear_advantage else '🔒 بدون تسلیحات هسته‌ای'}
🔗 متحدان: {len(user.allies)} کشور
⚛️ پیشرفت هسته‌ای: {user.nuclear_research_progress}%
    """
    
    bot.reply_to(message, profile_text)

# دستور /leaderboard
@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    user_id = message.from_user.id
    
    if check_spam(user_id):
        return
    
    # به روزرسانی اقتصاد همه کاربران
    for user in users_db.values():
        user.update_economy()
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🏦 اقتصاد", callback_data="leaderboard_economy"),
        types.InlineKeyboardButton("⚔️ نظامی", callback_data="leaderboard_military")
    )
    markup.row(
        types.InlineKeyboardButton("🔬 تکنولوژی", callback_data="leaderboard_technology"),
        types.InlineKeyboardButton("🌟 نفوذ", callback_data="leaderboard_influence")
    )
    markup.row(types.InlineKeyboardButton("🏆 امتیاز کلی", callback_data="leaderboard_total"))
    
    bot.reply_to(message, "🎯 **جدول رتبه‌بندی جهانی**\n\nلطفاً معیار رتبه‌بندی را انتخاب کنید:", reply_markup=markup)

# هندلر برای لیدربرد
@bot.callback_query_handler(func=lambda call: call.data.startswith('leaderboard_'))
def handle_leaderboard_selection(call):
    category = call.data.replace("leaderboard_", "")
    
    # مرتب‌سازی کاربران بر اساس معیار انتخاب شده
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
    elif category == "influence":
        sorted_users = sorted(users_db.values(), key=lambda x: x.influence, reverse=True)
        title = "🌟 10 کشور برتر از نظر نفوذ جهانی"
        field = "نفوذ"
    else:  # total
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
        elif category == "influence":
            value = user.influence
        else:
            value = user.calculate_total_score()
        
        leaderboard_text += f"{i}️⃣ **{user.country_name}**\n"
        leaderboard_text += f"   👤 {user.username}\n"
        leaderboard_text += f"   📊 {field}: {value:,.0f}\n"
        leaderboard_text += f"   👑 {user.leader['name']}\n\n"
    
    bot.edit_message_text(
        leaderboard_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

# دستور /allies
@bot.message_handler(commands=['allies'])
def allies_command(message):
    user_id = message.from_user.id
    
    if check_spam(user_id):
        return
    
    user = users_db.get(user_id)
    if not user:
        bot.reply_to(message, "❌ شما هنوز ثبت نام نکرده‌اید! /start")
        return
    
    # پیدا کردن کاربران قابل اتحاد
    potential_allies = [u for u in users_db.values() if u.user_id != user_id and u.user_id not in user.allies]
    
    if not potential_allies:
        bot.reply_to(message, "❌ هیچ کشوری برای ایجاد اتحاد موجود نیست!")
        return
    
    markup = types.InlineKeyboardMarkup()
    for ally in potential_allies[:10]:
        markup.add(types.InlineKeyboardButton(
            f"🤝 {ally.country_name} ({ally.username})",
            callback_data=f"ally_{ally.user_id}"
        ))
    
    markup.add(types.InlineKeyboardButton("📋 متحدان فعلی", callback_data="view_allies"))
    
    bot.reply_to(message, 
        "🤝 **مدیریت اتحادها**\n\nبرای ایجاد اتحاد جدید یک کشور را انتخاب کنید:",
        reply_markup=markup
    )

# هندلر برای متحدان
@bot.callback_query_handler(func=lambda call: call.data.startswith('ally_') or call.data == 'view_allies')
def handle_allies_selection(call):
    data = call.data
    
    if data == "view_allies":
        user_id = call.from_user.id
        user = users_db.get(user_id)
        
        if not user or not user.allies:
            bot.answer_callback_query(call.id, "❌ شما هیچ متحدی ندارید!")
            return
        
        allies_text = "🤝 **متحدان شما:**\n\n"
        for ally_id in user.allies:
            ally = users_db.get(ally_id)
            if ally:
                allies_text += f"• {ally.country_name} (@{ally.username})\n"
        
        bot.edit_message_text(
            allies_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return
    
    target_user_id = int(data.replace("ally_", ""))
    user_id = call.from_user.id
    
    user = users_db.get(user_id)
    target = users_db.get(target_user_id)
    
    if not user or not target:
        bot.answer_callback_query(call.id, "❌ خطا در پیدا کردن کاربر!")
        return
    
    # ایجاد اتحاد
    user.allies.append(target_user_id)
    target.allies.append(user_id)
    
    bot.edit_message_text(
        f"✅ **اتحاد ایجاد شد!**\n\nکشور شما و {target.country_name} هم‌اکنون متحد هستند.\n💡 مزایا: حمایت متقابل، تجارت آسان‌تر\n⚠️ هشدار: حمله به متحد جریمه دارد!",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

# هندلر برای پیام‌های معمولی
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    
    if check_spam(user_id):
        return
    
    if not message.text.startswith('/'):
        bot.reply_to(message,
            "🤖 **GeoPolitix Bot**\n\n"
            "لطفاً از دستورات استفاده کنید:\n"
            "/start - شروع بازی\n"
            "/profile - پروفایل\n"
            "/attack - حمله\n"
            "/allies - مدیریت متحدان\n"
            "/leaderboard - رتبه‌بندی\n"
            "/help - راهنما"
        )

# شروع ربات
print("🤖 GeoPolitix Bot is running...")
print("🎮 کشورها و رهبران واقعی اضافه شدند!")
print("🤝 سیستم اتحاد فعال شد!")
print("💰 اقتصاد خودکار فعال شد!")
bot.infinity_polling()
