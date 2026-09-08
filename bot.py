import sqlite3
import time
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

TOKEN = "8204501091:AAHNNc6bPzuMVb4q2GVlghJyJhEqPaEEfTg"
ADMIN_ID = 7795265338
CHANNEL_USERNAME = "@meet_mashhad_star"

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=64)

# پاک کردن کامل دستورات از سرور تلگرام تا دیگر در گروه نمایش داده نشوند
try:
    bot.delete_my_commands()
except Exception:
    pass
