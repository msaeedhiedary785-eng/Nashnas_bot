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

# توکن و اطلاعات ربات
TOKEN = "8949711651:AAFoUhwinj5UUDv09G_pP6K2lmZJ-XegBl4"
ADMIN_ID = 779265338
CHANNEL_USERNAME = "@meet_mashhad_star"
SUPPORT_USERNAME = "@Mr_saeed123"

bot = telebot.TeleBot(TOKEN, threaded=True)

# تنظیمات دیتابیس
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
        CREATE TABLE IF NOT EXISTS replies_map (
            receiver_id INTEGER,
            bot_msg_id INTEGER,
            sender_id INTEGER,
            PRIMARY KEY (receiver_id, bot_msg_id)
        )
    ''')
    conn.commit()
except Exception as e:
    print(f"DB Error: {e}")

def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

def show_main_menu(user_id, message_or_call_obj):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔗 لینک ناشناس من"), KeyboardButton("⚙️ تنظیمات"))
    markup.add(KeyboardButton("💬 پشتیبانی"))

    welcome_text = (
        "مشهد استاری 💫عزیز به ربات چت ناشناس استار خوش اومدین 💞\n\n"
        "با استفاده از این ربات می‌تونی لینک ناشناس خودت رو بگیری و به صورت کاملاً ناشناس پیام دریافت کنی."
    )
    
    if hasattr(message_or_call_obj, 'message'):
        try:
            bot.delete_message(message_or_call_obj.message.chat.id, message_or_call_obj.message.message_id)
        except Exception:
            pass
        bot.send_message(user_id, welcome_text, reply_markup=markup)
    else:
        bot.send_message(user_id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private':
        return

    user_id = message.from_user.id
    username = message.from_user.username

    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    except Exception:
        pass

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

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("send_"):
        try:
            target_id = int(args[1].replace("send_", ""))
            if target_id == user_id:
                bot.send_message(user_id, "خخخ نمی‌تونی به خودت پیام ناشناس بفرستی! 😄")
                show_main_menu(user_id, message)
                return
            
            bot.send_message(user_id, "پیام خودت را بفرست (متن، عکس، ویس یا فیلم) تا به صورت کاملاً ناشناس ارسال شود:")
            bot.register_next_step_handler(message, lambda m: forward_anonymous_message(m, target_id))
            return
        except ValueError:
            pass

    show_main_menu(user_id, message)

def forward_anonymous_message(message, target_id):
    if message.chat.type != 'private':
        return
    
    # اگر کاربر دکمه‌های منو را زد، حالت انتظار لغو شده و مستقیماً به منو هدایت می‌شود
    if message.text in ["🔗 لینک ناشناس من", "⚙️ تنظیمات", "💬 پشتیبانی"]:
        handle_text_messages(message)
        return

    try:
        bot.send_message(target_id, "📩 یک پیام ناشناس جدید داری:")
        copied_msg = bot.copy_message(target_id, message.chat.id, message.message_id)
        
        cursor.execute("INSERT OR REPLACE INTO replies_map (receiver_id, bot_msg_id, sender_id) VALUES (?, ?, ?)",
                       (target_id, copied_msg.message_id, message.from_user.id))
        conn.commit()

        bot.send_message(message.from_user.id, "✅ پیام ناشناس شما با موفقیت ارسال شد!")
        show_main_menu(message.from_user.id, message)
    except Exception:
        bot.send_message(message.from_user.id, "❌ ارسال پیام ناموفق بود (احتمالاً کاربر ربات را بلاک کرده است).")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_query(call):
    user_id = call.from_user.id
    if check_membership(user_id):
        bot.answer_callback_query(call.id, "عضویت شما تایید شد! 🎉")
        show_main_menu(user_id, call)
    else:
        bot.answer_callback_query(call.id, "هنوز در کانال عضو نشده‌اید! ❌", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    if message.chat.type != 'private':
        return
        
    user_id = message.from_user.id

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

    # بررسی ریپلی برای پاسخ دادن به پیام ناشناس
    if message.reply_to_message:
        cursor.execute("SELECT sender_id FROM replies_map WHERE receiver_id = ? AND bot_msg_id = ?",
                       (user_id, message.reply_to_message.message_id))
        row = cursor.fetchone()
        if row:
            original_sender_id = row[0]
            try:
                bot.send_message(original_sender_id, "📬 پاسخی به پیام ناشناس شما دریافت شد:")
                copied_reply = bot.copy_message(original_sender_id, message.chat.id, message.message_id)
                
                cursor.execute("INSERT OR REPLACE INTO replies_map (receiver_id, bot_msg_id, sender_id) VALUES (?, ?, ?)",
                               (original_sender_id, copied_reply.message_id, user_id))
                conn.commit()

                bot.send_message(user_id, "✅ پاسخ شما با موفقیت ارسال شد!")
            except Exception:
                bot.send_message(user_id, "❌ ارسال پاسخ ناموفق بود.")
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
        bot.send_message(user_id, f"💬 برای ارتباط با پشتیبان به آیدی درج شده مراجعه کنین:\n{SUPPORT_USERNAME}")
    else:
        bot.send_message(user_id, "دستور نامعتبر است. از دکمه‌های منو استفاده کنید.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(none_stop=True, interval=0, timeout=0, long_polling_timeout=5)
