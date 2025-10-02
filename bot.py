# geopolitix_bot.py
# Python 3.13 compatible
# Requires: pip install pytelegrambotapi

import sqlite3
import json
import threading
from datetime import datetime
import math

import telebot
from telebot import types

API_TOKEN = "8026391620:AAGsQTUZYbCFcvhrLVaUihcGFmsTZA52mHY"  # <-- اینجا توکن رو بذار

DB_PATH = "geopolitix.db"
# یک لاک ساده برای جلوگیری از race condition در sqlite (session-wide)
db_lock = threading.Lock()

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")


# ---------------------------
# Database helpers & init
# ---------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_lock:
        conn = get_conn()
        cur = conn.cursor()

        # users
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
          user_id INTEGER PRIMARY KEY,
          username TEXT,
          country_code TEXT,
          leader_id INTEGER,
          economy REAL DEFAULT 0,
          military_power REAL DEFAULT 0,
          technology REAL DEFAULT 0,
          influence REAL DEFAULT 0,
          resources TEXT DEFAULT '{}',
          allies TEXT DEFAULT '[]',
          nuclear_research_progress REAL DEFAULT 0,
          banned_until TIMESTAMP NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # countries
        cur.execute("""
        CREATE TABLE IF NOT EXISTS countries (
          code TEXT PRIMARY KEY,
          name_fa TEXT,
          region TEXT,
          nuclear_advantage INTEGER DEFAULT 0,
          base_economy INTEGER,
          base_military INTEGER,
          center_lat REAL,
          center_lon REAL
        );
        """)

        # leaders
        cur.execute("""
        CREATE TABLE IF NOT EXISTS leaders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT,
          country_code TEXT,
          power REAL,
          type TEXT,
          special_ability TEXT,
          description TEXT
        );
        """)

        # attacks (skeleton, may extend later)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attacks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          attacker_id INTEGER,
          defender_id INTEGER,
          launch_time TIMESTAMP,
          arrival_time TIMESTAMP,
          distance_km REAL,
          warhead_power REAL,
          status TEXT DEFAULT 'scheduled',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        conn.close()


# ---------------------------
# Seed data (countries + leaders)
# ---------------------------
COUNTRIES = [
    # nuclear countries
    ("US", "ایالات متحده آمریکا", "North America", 1, 1000, 950, 38.0, -97.0),
    ("RU", "روسیه", "Eurasia", 1, 900, 1000, 61.5, 105.0),
    ("CN", "چین", "Asia", 1, 850, 900, 35.0, 103.0),
    ("FR", "فرانسه", "Europe", 1, 600, 650, 46.0, 2.0),
    ("GB", "بریتانیا", "Europe", 1, 650, 620, 54.0, -2.0),
    ("IN", "هند", "Asia", 1, 500, 550, 21.0, 78.0),
    ("PK", "پاکستان", "Asia", 1, 200, 250, 30.0, 70.0),
    ("IL", "اسرائیل", "Asia", 1, 250, 300, 31.5, 34.8),
    ("KP", "کره شمالی", "Asia", 1, 150, 200, 40.0, 127.0),
    # non-nuclear
    ("IR", "ایران", "Asia", 0, 300, 350, 32.0, 53.0),
    ("DE", "آلمان", "Europe", 0, 700, 600, 51.0, 9.0),
    ("JP", "ژاپن", "Asia", 0, 800, 550, 36.0, 138.0),
    ("SA", "عربستان سعودی", "Asia", 0, 600, 400, 25.0, 45.0),
    ("TR", "ترکیه", "Europe/Asia", 0, 400, 420, 39.0, 35.0),
    ("BR", "برزیل", "South America", 0, 450, 300, -10.0, -55.0),
    ("CA", "کانادا", "North America", 0, 650, 500, 56.0, -106.0),
    ("KR", "کره جنوبی", "Asia", 0, 600, 520, 36.0, 128.0),
    ("AE", "امارات متحده عربی", "Asia", 0, 350, 300, 24.0, 54.0),
    ("SG", "سنگاپور", "Asia", 0, 400, 200, 1.3, 103.8),
]

LEADERS = [
    # minimal leader seeds; power in 0.7-0.95 range
    ("Joe Biden", "US", 0.9, "سیاستمدار", "دیپلماسی قوی", "رهبر آمریکا"),
    ("Vladimir Putin", "RU", 0.92, "استراتژیست", "قدرت نظامی", "رهبر روسیه"),
    ("Xi Jinping", "CN", 0.91, "سیاستمدار", "کنترل مرکزی", "رهبر چین"),
    ("Emmanuel Macron", "FR", 0.88, "سیاستمدار", "دیپلماسی", "رهبر فرانسه"),
    ("Rishi Sunak", "GB", 0.85, "اقتصاددان", "مدیریت اقتصاد", "رهبر بریتانیا"),
    ("Narendra Modi", "IN", 0.9, "سیاستمدار", "مردمی", "رهبر هند"),
    ("Ebrahim Raeisi", "IR", 0.78, "سیاستمدار", "داخلی", "رهبر ایران"),
    ("Mohammad bin Salman", "SA", 0.8, "اقتصاددان", "نفوذ منطقه‌ای", "رهبر عربستان"),
    ("Recep Tayyip Erdogan", "TR", 0.82, "سیاستمدار", "نفوذ منطقه‌ای", "رهبر ترکیه"),
    ("Benjamin Netanyahu", "IL", 0.86, "استراتژیست", "امنیتی", "رهبر اسرائیل"),
    ("Kim Jong Un", "KP", 0.75, "استراتژیست", "نظامی", "رهبر کره شمالی"),
    ("Olaf Scholz", "DE", 0.84, "اقتصاددان", "ثبات", "رهبر آلمان"),
]


def seed_data():
    with db_lock:
        conn = get_conn()
        cur = conn.cursor()

        # countries
        for c in COUNTRIES:
            cur.execute(
                """
                INSERT OR IGNORE INTO countries (code, name_fa, region, nuclear_advantage, base_economy, base_military, center_lat, center_lon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                c,
            )

        # leaders
        for l in LEADERS:
            cur.execute(
                """
                INSERT OR IGNORE INTO leaders (name, country_code, power, type, special_ability, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                l,
            )

        conn.commit()
        conn.close()


# ---------------------------
# Utility functions
# ---------------------------
def fetch_one(query, params=()):
    with db_lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        conn.close()
    return row


def fetch_all(query, params=()):
    with db_lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
    return rows


def execute(query, params=()):
    with db_lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        lastrowid = cur.lastrowid
        conn.close()
    return lastrowid


def assign_country_to_new_user(user_id, username):
    # انتخاب اولین کشور آزاد (که به هیچ کاربری اختصاص ندارد) به صورت ساده
    with db_lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT code FROM countries")
        all_countries = [r["code"] for r in cur.fetchall()]

        cur.execute("SELECT country_code FROM users WHERE country_code IS NOT NULL")
        taken = {r["country_code"] for r in cur.fetchall()}

        available = [c for c in all_countries if c not in taken]
        assigned = None
        if available:
            assigned = available[0]
        else:
            # اگر همه گرفته شدند: انتخاب تصادفی یا round-robin ساده بر اساس user_id
            assigned = all_countries[user_id % len(all_countries)]

        # find a leader from that country (first)
        cur.execute("SELECT id FROM leaders WHERE country_code = ? LIMIT 1", (assigned,))
        leader_row = cur.fetchone()
        leader_id = leader_row["id"] if leader_row else None

        # base economy/military from countries table
        cur.execute("SELECT base_economy, base_military FROM countries WHERE code = ?", (assigned,))
        c = cur.fetchone()
        base_economy = c["base_economy"] if c else 100
        base_military = c["base_military"] if c else 100

        # insert user
        cur.execute(
            """
            INSERT OR REPLACE INTO users (user_id, username, country_code, leader_id, economy, military_power, technology, influence, resources)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                assigned,
                leader_id,
                float(base_economy),
                float(base_military),
                50.0,  # default tech
                50.0,  # default influence
                json.dumps({"gold": 100, "oil": 50, "uranium": 0}),
            ),
        )
        conn.commit()
        conn.close()
    return assigned, leader_id


def format_profile_row(row):
    resources = json.loads(row["resources"]) if row["resources"] else {}
    text = (
        f"👤 <b>{row['username']}</b>\n"
        f"🏳️ کشور: <b>{row['country_code']}</b>\n"
        f"⚖️ اقتصاد: <b>{row['economy']:.1f}</b>\n"
        f"⚔️ قدرت نظامی: <b>{row['military_power']:.1f}</b>\n"
        f"🔬 تکنولوژی: <b>{row['technology']:.1f}</b>\n"
        f"🌐 نفوذ: <b>{row['influence']:.1f}</b>\n"
        f"⛏️ منابع: {', '.join([f'{k}:{v}' for k, v in resources.items()])}\n"
        f"🕒 عضویت از: {row['created_at']}"
    )
    return text


def compute_score(row):
    # وزن‌های پیشنهادی: economy 0.4, military 0.35, tech 0.15, influence 0.1
    return (
        (row["economy"] or 0) * 0.4
        + (row["military_power"] or 0) * 0.35
        + (row["technology"] or 0) * 0.15
        + (row["influence"] or 0) * 0.1
    )


# ---------------------------
# Bot command handlers
# ---------------------------
@bot.message_handler(commands=["start"])
def handle_start(message: telebot.types.Message):
    user = message.from_user
    user_id = user.id
    username = user.username or f"{user.first_name or ''} {user.last_name or ''}".strip()

    existing = fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing:
        bot.reply_to(message, f"👋 خوش برگشتی، <b>{username}</b>!\nاز قبل یک کشور به شما تخصیص داده شده است.\nبرای دیدن پروفایل /profile را بزنید.")
        return

    assigned_country, leader_id = assign_country_to_new_user(user_id, username)
    bot.reply_to(
        message,
        (
            f"🎉 خوش آمدی <b>{username}</b>!\n"
            f"کشور شما: <b>{assigned_country}</b>\n"
            f"رهبر شما: <b>{leader_id if leader_id else 'بدون رهبر'}</b>\n"
            "برای مشاهدهٔ جزئیات پروفایل /profile را بزنید."
        ),
    )


@bot.message_handler(commands=["profile"])
def handle_profile(message: telebot.types.Message):
    user = message.from_user
    user_id = user.id

    row = fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not row:
        bot.reply_to(message, "شما هنوز ثبت‌نام نکرده‌اید. برای شروع /start را بزنید.")
        return

    text = format_profile_row(row)
    bot.reply_to(message, text)


@bot.message_handler(commands=["leaderboard"])
def handle_leaderboard(message: telebot.types.Message):
    # نمایش کیبورد اینلاین برای انتخاب فیلتر
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("🏦 اقتصاد", callback_data="lb_economy"),
        types.InlineKeyboardButton("⚔️ نظامی", callback_data="lb_military"),
        types.InlineKeyboardButton("🔬 تکنولوژی", callback_data="lb_technology"),
        types.InlineKeyboardButton("🌟 نفوذ", callback_data="lb_influence"),
        types.InlineKeyboardButton("🏆 امتیاز کلی", callback_data="lb_score"),
    ]
    # جمع دو‌به‌دو در ردیف‌ها قرار می‌گیرند
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i : i + 2])
    bot.reply_to(message, "📊 فیلتر مورد نظر برای لیدربرد را انتخاب کنید:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("lb_"))
def callback_leaderboard(call: types.CallbackQuery):
    data = call.data  # e.g., lb_economy
    field = data.split("_", 1)[1]

    if field == "economy":
        rows = fetch_all("SELECT user_id, username, economy FROM users ORDER BY economy DESC LIMIT 10")
        title = "🏦 لیدربرد - اقتصاد"
        lines = [f"{i+1}. {r['username']} — {r['economy']:.1f}" for i, r in enumerate(rows)]
    elif field == "military":
        rows = fetch_all("SELECT user_id, username, military_power FROM users ORDER BY military_power DESC LIMIT 10")
        title = "⚔️ لیدربرد - قدرت نظامی"
        lines = [f"{i+1}. {r['username']} — {r['military_power']:.1f}" for i, r in enumerate(rows)]
    elif field == "technology":
        rows = fetch_all("SELECT user_id, username, technology FROM users ORDER BY technology DESC LIMIT 10")
        title = "🔬 لیدربرد - تکنولوژی"
        lines = [f"{i+1}. {r['username']} — {r['technology']:.1f}" for i, r in enumerate(rows)]
    elif field == "influence":
        rows = fetch_all("SELECT user_id, username, influence FROM users ORDER BY influence DESC LIMIT 10")
        title = "🌟 لیدربرد - نفوذ"
        lines = [f"{i+1}. {r['username']} — {r['influence']:.1f}" for i, r in enumerate(rows)]
    elif field == "score":
        rows = fetch_all("SELECT user_id, username, economy, military_power, technology, influence FROM users")
        scored = sorted(rows, key=lambda r: compute_score(r), reverse=True)[:10]
        title = "🏆 لیدربرد - امتیاز کلی"
        lines = [f"{i+1}. {r['username']} — {compute_score(r):.1f}" for i, r in enumerate(scored)]
    else:
        bot.answer_callback_query(call.id, "فیلتر نامشخص.")
        return

    if not lines:
        text = title + "\n\nهیچ کاربری پیدا نشد."
    else:
        text = title + "\n\n" + "\n".join(lines)

    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text)
    except Exception:
        # اگر ادیت پیام ممکن نبود (مثلاً از طرف کاربر دیگری) فقط پاسخ جدید بفرست
        bot.send_message(call.message.chat.id, text)


# ---------------------------
# Startup
# ---------------------------
if __name__ == "__main__":
    print("Initializing DB and seeding data...")
    init_db()
    seed_data()
    print("Bot is polling. Press Ctrl+C to stop.")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
