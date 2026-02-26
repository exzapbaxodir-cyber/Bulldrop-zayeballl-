import asyncio
import threading
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask, render_template
from config import TOKEN, ADMIN_ID

# ======================
# Telegram bot setup
# ======================
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ======================
# Database setup
# ======================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 5,
    referrals INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS promocodes (
    code TEXT PRIMARY KEY,
    reward INTEGER
)
""")
conn.commit()

# ======================
# Flask web admin panel
# ======================
app = Flask(__name__)

@app.route("/")
def index():
    users = cursor.execute("SELECT user_id, balance, referrals FROM users").fetchall()
    return render_template("index.html", users=users)

def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()

# ======================
# Telegram handlers
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    await message.answer("🎉 Xush kelibsiz! /balance bilan balansni tekshiring.")

@dp.message_handler(commands=['balance'])
async def balance(message: types.Message):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    bal = cursor.fetchone()[0]
    await message.answer(f"💰 Balans: {bal} coin")

# O‘yinlar bo‘yicha maslahat
@dp.message_handler(lambda message: message.text.lower() in ['narvon','sapyor','crash','gildirak','minora'])
async def game_advice(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    if bal < 1:
        await message.answer("❌ Coin yetarli emas")
        return
    cursor.execute("UPDATE users SET balance = balance - 1 WHERE user_id=?", (user_id,))
    conn.commit()

    game = message.text.lower()
    advice = ""
    if game == "narvon":
        advice = f"{random.randint(1,7)} pog'onagacha boring"
    elif game == "sapyor":
        advice = f"Xavfsiz katak: {random.randint(1,25)}"
    elif game == "crash":
        advice = f"x{round(random.uniform(1.5,3.5),2)} da chiqing"
    elif game == "gildirak":
        advice = random.choice(["Qizil","Yashil","Ko‘k"])
    elif game == "minora":
        advice = f"{random.randint(1,10)} qavatgacha boring"

    await message.answer(f"💡 Maslahat:\n{advice}")

# ======================
# Run bot
# ======================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
