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

TOKEN = "8204501091:AAHNNc6bPzuMVb4q2GVlghJyJhEqPaEEfTg"
ADMIN_ID = 779265338
CHANNEL_USERNAME = "@meet_mashhad_star"

bot = telebot.TeleBot(TOKEN, threaded=True)

try:
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
except Exception as e:
    print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(none_stop=True, interval=0, timeout=20)
