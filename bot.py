import sqlite3
import time
import telebot
from telebot.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

TOKEN = "8204501091:AAHNNc6bPzuMVb4q2GVlghJyJhEqPaEEfTg"
ADMIN_ID = 7795265338
CHANNEL_USERNAME = "@meet_mashhad_star"

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=64)

try:
    bot.set_my_commands(
        [
            BotCommand("start", "شروع مجدد"),
            BotCommand("mylink", "لینک من"),
        ],
        scope=BotCommandScopeAllPrivateChats()
    )
except Exception:
    pass

init_conn = sqlite3.connect("anon_bot.db", check_same_thread=False)
init_cursor = init_conn.cursor()
init_cursor.execute("PRAGMA journal_mode=WAL;")
init_cursor.execute("PRAGMA synchronous=NORMAL;")
init_cursor.execute(
    "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, target_id INTEGER)"
)
init_cursor.execute(
    "CREATE TABLE IF NOT EXISTS all_users (user_id INTEGER PRIMARY KEY)"
)
init_cursor.execute(
    "CREATE TABLE IF NOT EXISTS reply_map (sent_msg_id INTEGER, sender_id INTEGER, target_id INTEGER)"
)
init_conn.commit()
init_conn.close()

JOIN_CACHE = {}

def get_db():
    conn = sqlite3.connect("anon_bot.db", check_same_thread=False)
    return conn, conn.cursor()

def check_join_fast(user_id, force_check=False):
    now = time.time()
    if not force_check and user_id in JOIN_CACHE and (now - JOIN_CACHE[user_id]["time"]) < 3600:
        return JOIN_CACHE[user_id]["status"]

    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        is_member = member.status in ["creator", "administrator", "member"]
        JOIN_CACHE[user_id] = {"status": is_member, "time": now}
        return is_member
    except Exception:
        return True

def get_join_markup():
    markup = InlineKeyboardMarkup()
    channel_link = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    markup.add(InlineKeyboardButton("📢 عضویت در کانال", url=channel_link))
    markup.add(
        InlineKeyboardButton("✅ عضو شدم / بررسی", callback_data="check_membership")
    )
    return markup

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🔗 دریافت لینک من"))
    markup.row(KeyboardButton("❓ راهنما"), KeyboardButton("⚙️ تنظیمات"))
    return markup

def get_cancel_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("❌ لغو و خروج از چت"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def callback_check(call):
    user_id = call.from_user.id
    if user_id in JOIN_CACHE:
        del JOIN_CACHE[user_id]

    conn, cursor = get_db()
    try:
        if check_join_fast(user_id, force_check=True):
            try:
                bot.answer_callback_query(
                    call.id, text="✅ عضویت تایید شد!", show_alert=False
                )
                bot.delete_message(user_id, call.message.message_id)
            except Exception:
                pass

            cursor.execute("SELECT target_id FROM users WHERE user_id=?", (user_id,))
            res = cursor.fetchone()

            if res and res[0] is not None:
                text = (
                    "به ربات چت ناشناس مشهد استار خوش آمدید ✨️\n\n"
                    "📥 <b>چت شما به لینک خصوصی متصل شد.</b>\n\n"
                    "هر پیامی بنویسید فوراً برای مخاطب ارسال می‌شود.\nبرای لغو اتصال، روی دکمه زیر بزنید:"
                )
                bot.send_message(
                    user_id,
                    text,
                    reply_markup=get_cancel_menu(),
                    parse_mode="HTML",
                )
            else:
                text = "به ربات چت ناشناس مشهد استار خوش آمدید ✨️\n\nچه کاری می‌تونم براتون انجام بدم؟"
                bot.send_message(user_id, text, reply_markup=get_main_menu())
        else:
            try:
                bot.answer_callback_query(
                    call.id,
                    text="❌ هنوز عضو کانال نشده‌اید!",
                    show_alert=True,
                )
            except Exception:
                pass
    finally:
        conn.close()

@bot.message_handler(func=lambda message: message.chat.type != "private")
def ignore_groups(message):
    return

@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    conn, cursor = get_db()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO all_users (user_id) VALUES (?)", (user_id,)
        )
        conn.commit()

        text_args = message.text.split()
        target_id = None

        if len(text_args) > 1:
            target_id = text_args[1]
            if str(user_id) == str(target_id):
                bot.send_message(user_id, "❌ نمی‌توانی به خودت پیام ناشناس بفرستی!")
                return

            cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, target_id) VALUES (?, ?)",
                (user_id, int(target_id)),
            )
            conn.commit()
        else:
            cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()

        if not check_join_fast(user_id):
            bot.send_message(
                user_id,
                "⚠️ <b>لطفاً ابتدا در کانال ما عضو شوید:</b>\n\nبرای استفاده از ربات و ارسال پیام ناشناس، عضویت در کانال زیر الزامی است.",
                reply_markup=get_join_markup(),
                parse_mode="HTML",
            )
            return

        if target_id:
            msg_text = (
                "به ربات چت ناشناس مشهد استار خوش آمدید ✨️\n\n"
                "📥 <b>چت شما به لینک خصوصی متصل شد.</b>\n\n"
                "هر پیامی بنویسید فوراً برای مخاطب ارسال می‌شود.\nبرای لغو اتصال، روی دکمه زیر بزنید:"
            )
            bot.send_message(
                user_id,
                msg_text,
                reply_markup=get_cancel_menu(),
                parse_mode="HTML",
            )
        else:
            msg_text = "به ربات چت ناشناس مشهد استار خوش آمدید ✨️\n\nچه کاری می‌تونم براتون انجام بدم؟"
            bot.send_message(user_id, msg_text, reply_markup=get_main_menu())
    finally:
        conn.close()

@bot.message_handler(commands=["mylink"])
def send_mylink(message):
    user_id = message.chat.id

    if not check_join_fast(user_id):
        bot.send_message(
            user_id,
            "⚠️ <b>لطفاً ابتدا در کانال ما عضو شوید:</b>",
            reply_markup=get_join_markup(),
            parse_mode="HTML",
        )
        return

    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"

    msg = (
        "مشهد استاری محترم 👋✨\n\n"
        "روی لینک زیر کلیک کن و هر حرف، نظر، حرف ناگفته یا انتقادی که داری رو خیلی راحت برام بنویس و بفرست.\n"
        "هویتت کاملاً مخفی می‌مونه و من اصلاً نمی‌فهمم پیام از طرف کی بوده! 🤫💬\n\n"
        f"🔗 لینک اختصاصی شما:\n<a href='{link}'>{link}</a>"
    )

    bot.send_message(
        user_id,
        msg,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@bot.message_handler(commands=["stats"])
def send_stats(message):
    if message.chat.id == ADMIN_ID:
        conn, cursor = get_db()
        try:
            cursor.execute("SELECT COUNT(*) FROM all_users")
            count = cursor.fetchone()[0]
            bot.send_message(
                ADMIN_ID, f"📊 تعداد کل کاربران ثبت‌شده در ربات: {count} نفر"
            )
        finally:
            conn.close()

@bot.message_handler(func=lambda message: message.text == "❌ لغو و خروج از چت")
def handle_cancel(message):
    user_id = message.chat.id
    conn, cursor = get_db()
    try:
        cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    bot.send_message(
        user_id,
        "✅ حالت ارسال پیام ناشناس لغو شد.\n\nبا سپاس از شما مشهد استاری عزیز ❤️",
        reply_markup=get_main_menu(),
    )

@bot.message_handler(
    func=lambda message: message.text
    in ["🔗 دریافت لینک من", "❓ راهنما", "⚙️ تنظیمات"]
)
def handle_menu_buttons(message):
    user_id = message.chat.id

    if not check_join_fast(user_id):
        bot.send_message(
            user_id,
            "⚠️ <b>لطفاً ابتدا در کانال ما عضو شوید:</b>",
            reply_markup=get_join_markup(),
            parse_mode="HTML",
        )
        return

    text = message.text

    if text == "🔗 دریافت لینک من":
        send_mylink(message)

    elif text == "❓ راهنما":
        help_text = (
            "📖 <b>راهنمای استفاده:</b>\n\n"
            "1️⃣ روی «دریافت لینک من» بزنید.\n"
            "2️⃣ لینک خود را برای دیگران بفرستید.\n"
            "3️⃣ اگر کسی به شما پیام ناشناس داد، با <b>Reply</b> روی آن جواب دهید."
        )
        bot.send_message(user_id, help_text, parse_mode="HTML")

    elif text == "⚙️ تنظیمات":
        bot.send_message(
            user_id, "⚙️ تنظیمات در حال حاضر پیش‌فرض قرار دارند."
        )

@bot.message_handler(
    func=lambda message: True,
    content_types=["text", "photo", "voice", "sticker", "video"],
)
def handle_messages(message):
    sender_id = message.chat.id

    if message.text in [
        "🔗 دریافت لینک من",
        "❓ راهنما",
        "⚙️ تنظیمات",
        "❌ لغو و خروج از چت",
    ]:
        return

    if not check_join_fast(sender_id):
        bot.send_message(
            sender_id,
            "⚠️ <b>جهت ارسال پیام باید ابتدا عضو کانال شوید:</b>",
            reply_markup=get_join_markup(),
            parse_mode="HTML",
        )
        return

    conn, cursor = get_db()
    try:
        if message.reply_to_message:
            replied_msg_id = message.reply_to_message.message_id
            cursor.execute(
                "SELECT sender_id FROM reply_map WHERE sent_msg_id=? AND target_id=?",
                (replied_msg_id, sender_id),
            )
            res = cursor.fetchone()

            if res:
                original_sender_id = res[0]
                try:
                    bot.send_message(
                        original_sender_id,
                        "📩 <b>پاسخ به پیام ناشناس شما:</b>",
                        parse_mode="HTML",
                    )
                    bot.copy_message(
                        original_sender_id, sender_id, message.message_id
                    )
                    bot.send_message(
                        sender_id, "✅ پاسخ شما برای فرستنده ناشناس ارسال شد."
                    )
                    return
                except Exception:
                    bot.send_message(sender_id, "❌ ارسال پاسخ ناموفق بود.")
                    return

        cursor.execute("SELECT target_id FROM users WHERE user_id=?", (sender_id,))
        result = cursor.fetchone()

        if result and result[0] is not None:
            target_id = result[0]
            try:
                bot.send_message(
                    target_id,
                    "📩 <b>یک پیام ناشناس جدید داری:</b>\n<i>(می‌توانی روی این پیام Reply بزنی تا پاسخ بدی)</i>",
                    parse_mode="HTML",
                )
                sent_msg = bot.copy_message(
                    target_id, sender_id, message.message_id
                )

                cursor.execute(
                    "INSERT INTO reply_map (sent_msg_id, sender_id, target_id) VALUES (?, ?, ?)",
                    (sent_msg.message_id, sender_id, target_id),
                )
                conn.commit()

                bot.send_message(sender_id, "✅ پیام شما با موفقیت ارسال شد.")
            except Exception:
                bot.send_message(sender_id, "❌ خطایی در ارسال رخ داد.")
        else:
            bot.send_message(
                sender_id,
                "⚠️ شما در حال حاضر به کسی متصل نیستید. لطفاً روی لینک ناشناس شخص مورد نظر کلیک کنید.",
                reply_markup=get_main_menu(),
            )
    finally:
        conn.close()

if __name__ == "__main__":
    bot.infinity_polling(
        none_stop=True, interval=0, timeout=5, long_polling_timeout=5
    )
