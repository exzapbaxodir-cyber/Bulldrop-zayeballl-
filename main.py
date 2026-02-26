import asyncio
import threading
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from flask import Flask, render_template
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

# ===== Inline Tugmalar =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Narvon", callback_data="narvon"),
        InlineKeyboardButton("Sapyor", callback_data="sapyor"),
        InlineKeyboardButton("Crash", callback_data="crash"),
        InlineKeyboardButton("Gildirak", callback_data="gildirak"),
        InlineKeyboardButton("Minora", callback_data="minora"),
        InlineKeyboardButton("Balans", callback_data="balance"),
        InlineKeyboardButton("Promo kod", callback_data="promo")
    )
    return kb

# ===== /start handler =====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    if args.isdigit():
        ref_id = int(args)
        if ref_id != user_id:
            cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, balance, referrals) VALUES (?, ?, ?)", (user_id, 5, 0))
                cursor.execute("UPDATE users SET balance = balance + 3, referrals = referrals + 1 WHERE user_id=?", (ref_id,))
                conn.commit()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    await message.answer("🎉 Xush kelibsiz! Quyidagi tugmalardan foydalaning:", reply_markup=main_menu())

# ===== Callback handler =====
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    
    data = callback.data

    # Balansni tekshirish
    if data == "balance":
        await callback.message.answer(f"💰 Balans: {bal} coin", reply_markup=main_menu())
        return

    # Promo kod tugmasi
    if data == "promo":
        await callback.message.answer("💳 Promo kod kiriting format: PROMO <code>\nMasalan: PROMO TEST")
        return

    # Admin uchun balans qo'shish
    if user_id == ADMIN_ID:
        if data in ["narvon","sapyor","crash","gildirak","minora"]:
            cursor.execute("UPDATE users SET balance = balance + 10 WHERE user_id=?", (user_id,))
            conn.commit()
            await callback.message.answer(f"✅ 10 coin qo‘shildi (admin bonus)", reply_markup=main_menu())

    # Maslahatlar uchun coin ishlatish
    if data in ["narvon","sapyor","crash","gildirak","minora"]:
        if bal < 1:
            await callback.message.answer("❌ Coin yetarli emas", reply_markup=main_menu())
            return
        cursor.execute("UPDATE users SET balance = balance - 1 WHERE user_id=?", (user_id,))
        conn.commit()

        advice = ""
        if data == "narvon":
            steps = random.randint(1,7)
            advice = "🪜 " + "->".join(str(i+1) for i in range(steps))
        elif data == "sapyor":
            size = 5
            bombs = 3
            board = [['⬜' for _ in range(size)] for _ in range(size)]
            bomb_positions = random.sample(range(size*size), bombs)
            for pos in bomb_positions:
                row = pos // size
                col = pos % size
                board[row][col] = '🧨'
            advice = "\n".join("".join(row) for row in board)
        elif data == "crash":
            coef = round(random.uniform(1.2, 3.5), 2)
            advice = f"💡 Taxminiy to‘xtash x: {coef}x"
        elif data == "gildirak":
            wheel = ['🟦']*12 + ['🟩']*7 + ['🟥']*7 + ['🟪']
            choice = random.choice(wheel)
            visual = random.choices(wheel, k=10)
            advice = "".join(visual) + f"\n🎯 Taxminiy to'xtash rangi: {choice}"
        elif data == "minora":
            floors = 8
            directions = [random.choice(['⬅️','➡️']) for _ in range(floors)]
            advice = "\n".join(f"Qavat {i+1}: {dir}" for i, dir in enumerate(directions))

        await callback.message.answer(f"💡 Maslahat ({data.capitalize()}):\n{advice}", reply_markup=main_menu())

# ===== Promo kod matnli kiritish =====
@dp.message_handler(lambda message: message.text.upper().startswith("PROMO "))
async def promo_code(message: types.Message):
    code = message.text.split()[1].upper()
    cursor.execute("SELECT reward FROM promocodes WHERE code=?", (code,))
    res = cursor.fetchone()
    if res:
        reward = res[0]
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, message.from_user.id))
        conn.commit()
        await message.answer(f"🎁 Promokod qabul qilindi! {reward} coin qo‘shildi.", reply_markup=main_menu())
    else:
        await message.answer("❌ Noto‘g‘ri promokod!", reply_markup=main_menu())

# ===== Run bot =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
