import sqlite3
import time
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# توکن جدید و اطلاعات ربات
TOKEN = "8949711651:AAFoUhwinj5UUDv09G_pP6K2lmZJ-XegBl4"
ADMIN_ID = 779265338
CHANNEL_USERNAME = "@meet_mashhad_star"

bot = telebot.TeleBot(TOKEN, threaded=True)

# تنظیمات دیتابیس برای ذخیره کاربران و پیام‌ها
try:
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receiver_id INTEGER,
            sender_id INTEGER,
            message_text TEXT
        )
    ''')
    conn.commit()
except Exception as e:
    print(f"DB Error: {e}")

# تابع بررسی عضویت اجباری در کانال
def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

# دستور استارت
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # تفکیک کامل گروه و پی‌وی: اگر پیام در گروه بود، ربات هیچ واکنشی نشان ندهد
    if message.chat.type != 'private':
        return

    user_id = message.from_user.id
    username = message.from_user.username

    # ثبت کاربر در دیتابیس
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    except Exception:
        pass

    # بررسی عضویت اجباری در کانال
    if not check_membership(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("عضویت در کانال ⭐️", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("عضو شدم ✅", callback_data="check_join"))
        bot.send_message(
            user_id,
            "برای استفاده از ربات چت ناشناس، ابتدا باید در کانال زیر عضو شوید:",
            reply_markup=markup
        )
        return

    # بررسی اینکه آیا کاربر روی لینک ناشناس کسی کلیک کرده است یا خیر
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("send_"):
        try:
            target_id = int(args[1].replace("send_", ""))
            if target_id == user_id:
                bot.send_message(user_id, "خخخ نمی‌تونی به خودت پیام ناشناس بفرستی! 😄")
                return
            bot.send_message(user_id, "پیام خودت را بفرست (متن، عکس، ویس یا فیلم) تا به صورت کاملاً ناشناس ارسال شود:")
            bot.register_next_step_handler(message, lambda m: forward_anonymous_message(m, target_id))
            return
        except ValueError:
            pass

    # کیبورد اصلی پنل کاربری در پی‌وی
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔗 لینک ناشناس من"), KeyboardButton("⚙️ تنظیمات"))
    markup.add(KeyboardButton("💬 پشتیبانی"))

    welcome_text = (
        "سلام! به ربات چت ناشناس خوش آمدی. 🌹\n\n"
        "با استفاده از این ربات می‌تونی لینک ناشناس خودت رو بگیری و به صورت کاملاً ناشناس پیام دریافت کنی."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup)

# تابع ارسال پیام ناشناس
def forward_anonymous_message(message, target_id):
    if message.chat.type != 'private':
        return
    if message.text in ["🔗 لینک ناشناس من", "⚙️ تنظیمات", "💬 پشتیبانی"]:
        bot.send_message(message.from_user.id, "ارسال پیام لغو شد.")
        return

    try:
        bot.send_message(target_id, "📩 یک پیام ناشناس جدید داری:")
        bot.copy_message(target_id, message.chat.id, message.message_id)
        bot.send_message(message.from_user.id, "✅ پیام ناشناس شما با موفقیت ارسال شد!")
    except Exception:
        bot.send_message(message.from_user.id, "❌ ارسال پیام ناموفق بود (احتمالاً کاربر ربات را بلاک کرده است).")

# تایید دکمه شیشه‌ای عضویت در کانال
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_query(call):
    user_id = call.from_user.id
    if check_membership(user_id):
        bot.answer_callback_query(call.id, "عضویت شما تایید شد! 🎉")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        fake_message = call.message
        fake_message.text = "/start"
        send_welcome(fake_message)
    else:
        bot.answer_callback_query(call.id, "هنوز در کانال عضو نشده‌اید! ❌", show_alert=True)

# مدیریت دکمه‌های منوی شیشه‌ای و متنی
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_text_messages(message):
    user_id = message.from_user.id

    if not check_membership(user_id):
        bot.send_message(user_id, "لطفاً ابتدا در کانال عضو شوید تا ربات کار کند.")
        return

    if message.text == "🔗 لینک ناشناس من":
        bot_info = bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=send_{user_id}"
        bot.send_message(
            user_id,
            f"🔗 لینک ناشناس اختصاصی شما:\n\n{link}\n\nاین لینک رو برای دوستانت بفرست تا بتونن ناشناس بهت پیام بدن!"
        )
    elif message.text == "⚙️ تنظیمات":
        bot.send_message(user_id, "⚙️ بخش تنظیمات ربات (فعلا غیرفعال می‌باشد).")
    elif message.text == "💬 پشتیبانی":
        bot.send_message(user_id, f"💬 برای ارتباط با پشتیبانی به کانال زیر مراجعه کنید:\n{CHANNEL_USERNAME}")
    else:
        bot.send_message(user_id, "دستور نامعتبر است. از دکمه‌های منو استفاده کنید.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(none_stop=True, interval=0, timeout=20)
