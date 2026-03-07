import os
import logging
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7334992081"))

CHANNELS = [
    "@HackingToolshere",
    "@CYBERNOVA0"
]

# ================= INIT =================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DATABASE =================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
points INTEGER DEFAULT 0,
ref INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS redeem_codes(
code TEXT PRIMARY KEY,
reward INTEGER
)
""")

conn.commit()

# ================= MENU =================

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Balance"), KeyboardButton(text="🎁 Giveaway")],
        [KeyboardButton(text="👥 Referral"), KeyboardButton(text="🏆 Leaderboard")]
    ],
    resize_keyboard=True
)

# ================= FORCE JOIN =================

async def check_sub(user_id):
    try:
        for channel in CHANNELS:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == "left":
                return False
        return True
    except:
        return False


def join_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channels", url="https://t.me/HackingToolshere")],
        [InlineKeyboardButton(text="✅ Check", callback_data="checksub")]
    ])
    return kb

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref = None
        if len(args) > 1 and args[1].isdigit():
            ref = int(args[1])

        cursor.execute("INSERT INTO users VALUES(?,?,?)", (user_id, 0, ref))
        conn.commit()

        if ref:
            cursor.execute(
                "UPDATE users SET points=points+10 WHERE user_id=?",
                (ref,)
            )
            conn.commit()

    if not await check_sub(user_id):
        await message.answer("❌ Join channels first", reply_markup=join_kb())
        return

    await message.answer("🎉 Welcome Giveaway Bot", reply_markup=menu)

# ================= BALANCE =================

@dp.message(lambda m: m.text == "💰 Balance")
async def balance(message: types.Message):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchone()

    pts = data[0] if data else 0
    await message.answer(f"💰 Points: {pts}")

# ================= GIVEAWAY =================

@dp.message(lambda m: m.text == "🎁 Giveaway")
async def giveaway(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="reward_15")],
        [InlineKeyboardButton(text="🎁 Gift Card", callback_data="reward_30")],
        [InlineKeyboardButton(text="📱 Airtime", callback_data="reward_20")]
    ])

    await message.answer("Choose reward", reply_markup=kb)

# ================= REWARD REQUEST =================

@dp.callback_query(lambda c: c.data.startswith("reward_"))
async def reward(call: types.CallbackQuery):
    user_id = call.from_user.id
    amount = int(call.data.split("_")[1])

    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    points = cursor.fetchone()[0]

    if points < amount:
        await call.answer("❌ Not enough points", show_alert=True)
        return

    cursor.execute(
        "UPDATE users SET points=points-? WHERE user_id=?",
        (amount, user_id)
    )
    conn.commit()

    await bot.send_message(
        ADMIN_ID,
        f"🎁 Reward request\nUser: {user_id}\nPoints Used: {amount}"
    )

    await call.message.answer("⏳ Request sent to admin")

# ================= REDEEM =================

@dp.message(Command("redeem"))
async def redeem(message: types.Message):
    code = message.get_args()

    cursor.execute("SELECT reward FROM redeem_codes WHERE code=?", (code,))
    data = cursor.fetchone()

    if not data:
        await message.answer("❌ Invalid code")
        return

    reward = data[0]

    cursor.execute(
        "UPDATE users SET points=points+? WHERE user_id=?",
        (reward, message.from_user.id)
    )

    conn.commit()

    await message.answer(f"✅ Redeemed {reward} points")

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
