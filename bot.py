import sqlite3
import threading
import uuid
from flask import Flask
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

TOKEN = "8949711651:AAFoUhwinj5UUDv09G_pP6K2lmZJ-XegBl4"
ADMIN_ID = 779265338
CHANNEL_USERNAME = "@meet_mashhad_star"
SUPPORT_USERNAME = "@Mr_saeed123"

bot = telebot.TeleBot(TOKEN, threaded=True)

# اتصال به دیتابیس
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_tokens (
        user_id INTEGER PRIMARY KEY,
        random_token TEXT UNIQUE
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
cursor.execute('''
    CREATE TABLE IF NOT EXISTS blocks (
        blocker_id INTEGER,
        blocked_id INTEGER,
        PRIMARY KEY (blocker_id, blocked_id)
    )
''')
conn.commit()

def get_or_create_user_token(user_id):
    cursor.execute("SELECT random_token FROM user_tokens WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        token = uuid.uuid4().hex[:6]
        try:
            cursor.execute("INSERT INTO user_tokens (user_id, random_token) VALUES (?, ?)", (user_id, token))
            conn.commit()
        except:
            token = uuid.uuid4().hex[:8]
            cursor.execute("INSERT INTO user_tokens (user_id, random_token) VALUES (?, ?)", (user_id, token))
            conn.commit()
        return token

def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except:
        pass
    return False

def show_main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔗 لینک ناشناس من"), KeyboardButton("⚙️ تنظیمات"))
    markup.add(KeyboardButton("💬 پشتیبانی"))
    
    text = (
        "مشهد استاری 💫عزیز به ربات چت ناشناس استار خوش اومدین 💞\n\n"
        "با استفاده از این ربات می‌تونی لینک ناشناس خودت رو بگیری و به صورت کاملاً ناشناس پیام دریافت کنی."
    )
    bot.send_message(user_id, text, reply_markup=markup)

def show_block_list(user_id):
    cursor.execute("SELECT blocked_id FROM blocks WHERE blocker_id = ?", (user_id,))
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(user_id, "📋 لیست بلاکی‌های شما خالی است.")
        return
        
    markup = InlineKeyboardMarkup()
    for row in rows:
        b_id = row[0]
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (b_id,))
        u_row = cursor.fetchone()
        uname = f"@{u_row[0]}" if u_row and u_row[0] else "کاربر ناشناس"
        markup.add(InlineKeyboardButton(f"🔓 آزادسازی {uname}", callback_data=f"unblock_{b_id}"))
        
    bot.send_message(user_id, "⚙️ لیست کاربرانی که بلاک کرده‌اید:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private':
        return

    user_id = message.from_user.id
    username = message.from_user.username

    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()

    if not check_membership(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("عضویت در کانال ⭐️", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("عضو شدم ✅", callback_data="check_join"))
        bot.send_message(user_id, "برای استفاده از ربات، ابتدا در کانال زیر عضو شوید:", reply_markup=markup)
        return

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("send_"):
        token_arg = args[1].replace("send_", "")
        cursor.execute("SELECT user_id FROM user_tokens WHERE random_token = ?", (token_arg,))
        t_row = cursor.fetchone()
        
        if not t_row:
            bot.send_message(user_id, "❌ لینک ناشناس نامعتبر است.")
            show_main_menu(user_id)
            return
            
        target_id = t_row[0]
        if target_id == user_id:
            bot.send_message(user_id, "نمی‌تونی به خودت پیام بفرستی! 😄")
            show_main_menu(user_id)
            return
        
        cursor.execute("SELECT * FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (target_id, user_id))
        if cursor.fetchone():
            bot.send_message(user_id, "❌ این کاربر شما را بلاک کرده است.")
            show_main_menu(user_id)
            return
        
        bot.send_message(user_id, "پیام خودت را بفرست (متن، عکس، ویس...):")
        bot.register_next_step_handler(message, lambda m: forward_anonymous_message(m, target_id))
        return

    show_main_menu(user_id)

def forward_anonymous_message(message, target_id):
    if message.chat.type != 'private':
        return
    if message.text in ["🔗 لینک ناشناس من", "⚙️ تنظیمات", "💬 پشتیبانی"]:
        handle_text(message)
        return

    try:
        bot.send_message(target_id, "📩 یک پیام ناشناس جدید داری:")
        copied = bot.copy_message(target_id, message.chat.id, message.message_id)
        
        cursor.execute("INSERT OR REPLACE INTO replies_map (receiver_id, bot_msg_id, sender_id) VALUES (?, ?, ?)",
                       (target_id, copied.message_id, message.from_user.id))
        conn.commit()

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("پیامتو دیدم 👀", callback_data=f"seen_{message.from_user.id}"),
            InlineKeyboardButton("پاسخ ↩", callback_data=f"reply_{message.from_user.id}"),
            InlineKeyboardButton("گزارش تخلف ⚠️", callback_data=f"report_{message.from_user.id}"),
            InlineKeyboardButton("بلاک 🚫", callback_data=f"block_{message.from_user.id}")
        )
        bot.send_message(target_id, "گزینه‌های تعامل با پیام:", reply_markup=markup)
        bot.send_message(message.from_user.id, "✅ پیام ناشناس شما با موفقیت ارسال شد!")
    except:
        bot.send_message(message.from_user.id, "❌ ارسال پیام ناموفق بود.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data == "check_join":
        if check_membership(user_id):
            bot.answer_callback_query(call.id, "عضویت تایید شد! 🎉")
            show_main_menu(user_id)
        else:
            bot.answer_callback_query(call.id, "هنوز عضو نشده‌اید! ❌", show_alert=True)
        return

    if data.startswith("unblock_"):
        unblock_id = int(data.split("_")[1])
        cursor.execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (user_id, unblock_id))
        conn.commit()
        bot.answer_callback_query(call.id, "کاربر آزاد شد ✅", show_alert=True)
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        show_block_list(user_id)
        return

    try:
        action, sender_id_str = data.split("_")
        sender_id = int(sender_id_str)
    except:
        return

    if action == "seen":
        bot.answer_callback_query(call.id, "ثبت شد ✅")
        try:
            bot.send_message(sender_id, "👀 مخاطب پیام شما را دید!")
        except:
            pass
    elif action == "reply":
        bot.answer_callback_query(call.id, "حالت پاسخ فعال شد ↩")
        msg = bot.send_message(user_id, "💬 پاسخ خود را بفرستید:")
        bot.register_next_step_handler(msg, lambda m: send_direct_reply(m, sender_id))
    elif action == "report":
        bot.answer_callback_query(call.id, "گزارش شد.", show_alert=True)
    elif action == "block":
        cursor.execute("INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", (user_id, sender_id))
        conn.commit()
        bot.answer_callback_query(call.id, "بلاک شد 🚫", show_alert=True)
        try:
            bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
        except:
            pass

def send_direct_reply(message, original_sender_id):
    if message.chat.type != 'private':
        return
    if message.text in ["🔗 لینک ناشناس من", "⚙️ تنظیمات", "💬 پشتیبانی"]:
        handle_text(message)
        return

    try:
        bot.send_message(original_sender_id, "📬 پاسخی به پیام ناشناس شما آمد:")
        copied = bot.copy_message(original_sender_id, message.chat.id, message.message_id)
        
        cursor.execute("INSERT OR REPLACE INTO replies_map (receiver_id, bot_msg_id, sender_id) VALUES (?, ?, ?)",
                       (original_sender_id, copied.message_id, message.from_user.id))
        conn.commit()

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("پیامتو دیدم 👀", callback_data=f"seen_{message.from_user.id}"),
            InlineKeyboardButton("پاسخ ↩", callback_data=f"reply_{message.from_user.id}"),
            InlineKeyboardButton("گزارش تخلف ⚠️", callback_data=f"report_{message.from_user.id}"),
            InlineKeyboardButton("بلاک 🚫", callback_data=f"block_{message.from_user.id}")
        )
        bot.send_message(original_sender_id, "گزینه‌های تعامل با پیام:", reply_markup=markup)
        bot.send_message(message.from_user.id, "✅ پاسخ ارسال شد!")
    except:
        bot.send_message(message.from_user.id, "❌ ارسال پاسخ ناموفق بود.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.chat.type != 'private':
        return
        
    user_id = message.from_user.id
    text = message.text

    if not check_membership(user_id):
        return

    if text == "🔗 لینک ناشناس من":
        bot_info = bot.get_me()
        token = get_or_create_user_token(user_id)
        link = f"https://t.me/{bot_info.username}?start=send_{token}"
        bot.send_message(user_id, f"🔗 لینک ناشناس اختصاصی شما:\n\n{link}")
    elif text == "⚙️ تنظیمات":
        show_block_list(user_id)
    elif text == "💬 پشتیبانی":
        bot.send_message(user_id, f"💬 آیدی پشتیبانی:\n{SUPPORT_USERNAME}")
    else:
        bot.send_message(user_id, "لطفاً از دکمه‌های منو استفاده کنید.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(none_stop=True, interval=1, timeout=20)
