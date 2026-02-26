import asyncio
import threading
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask, render_template, request
from config import TOKEN, ADMIN_ID

# ===== Telegram bot setup =====
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ===== Database setup =====
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

# ===== Flask web admin panel =====
app = Flask(__name__)

@app.route("/")
def index():
    users = cursor.execute("SELECT user_id, balance, referrals FROM users").fetchall()
    return render_template("index.html", users=users)

def run_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask).start()

# ===== Telegram handlers =====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    # Referral tizimi
    if args.isdigit():
        ref_id = int(args)
        if ref_id != user_id:
            cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, balance, referrals) VALUES (?, ?, ?)", (user_id, 5, 0))
                cursor.execute("UPDATE users SET balance = balance + 3, referrals = referrals + 1 WHERE user_id=?", (ref_id,))
                conn.commit()
    # Yangi foydalanuvchi
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

# ===== O'yinlar bo'yicha kreativ maslahatlar =====
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
        # Narvon: pog'ona raqamlari
        steps = random.randint(1,7)
        advice = "🪜 " + "->".join(str(i+1) for i in range(steps))

    elif game == "sapyor":
        # Sapyor: 5x5 xarita, 3 bomba
        size = 5
        bombs = 3
        board = [['⬜' for _ in range(size)] for _ in range(size)]
        bomb_positions = random.sample(range(size*size), bombs)
        for pos in bomb_positions:
            row = pos // size
            col = pos % size
            board[row][col] = '🧨'
        advice = "\n".join("".join(row) for row in board)

    elif game == "crash":
        # Crash: x koeffitsienti
        coef = round(random.uniform(1.2, 3.5), 2)
        advice = f"💡 Taxminiy to‘xtash x: {coef}x"

    elif game == "gildirak":
        # Gildirak: ranglar 🟦 12, 🟩 7, 🟥 7, 🟪 1
        wheel = ['🟦']*12 + ['🟩']*7 + ['🟥']*7 + ['🟪']
        choice = random.choice(wheel)
        visual = random.choices(wheel, k=10)
        advice = "".join(visual) + f"\n🎯 Taxminiy to'xtash rangi: {choice}"

    elif game == "minora":
        # Minora: 8 qavat, chap/ong
        floors = 8
        directions = [random.choice(['⬅️','➡️']) for _ in range(floors)]
        advice = "\n".join(f"Qavat {i+1}: {dir}" for i, dir in enumerate(directions))

    await message.answer(f"💡 Maslahat ({game.capitalize()}):\n{advice}")

# ===== Promokod bo‘limi =====
@dp.message_handler(lambda message: message.text.lower().startswith("promo "))
async def promo(message: types.Message):
    code = message.text.split()[1].upper()
    cursor.execute("SELECT reward FROM promocodes WHERE code=?", (code,))
    res = cursor.fetchone()
    if res:
        reward = res[0]
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, message.from_user.id))
        conn.commit()
        await message.answer(f"🎁 Promokod qabul qilindi! {reward} coin qo‘shildi.")
    else:
        await message.answer("❌ Noto‘g‘ri promokod!")

# ===== Run bot =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
