import os
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

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
dp = Dispatcher(bot)

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

menu = ReplyKeyboardMarkup(resize_keyboard=True)

menu.add(
    KeyboardButton("💰 Balance"),
    KeyboardButton("🎁 Giveaway")
)

menu.add(
    KeyboardButton("👥 Referral"),
    KeyboardButton("🏆 Leaderboard")
)

# ================= FORCE JOIN =================

async def check_sub(user_id):
    try:
        for channel in CHANNELS:
            m = await bot.get_chat_member(channel, user_id)
            if m.status == "left":
                return False
        return True
    except:
        return False

def join_kb():
    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("📢 Join Channels", url="https://t.me/HackingToolshere")
    )

    kb.add(
        InlineKeyboardButton("✅ Check", callback_data="checksub")
    )

    return kb

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    user_id = message.from_user.id
    args = message.get_args()

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref = int(args) if args.isdigit() else None

        if ref == user_id:
            ref = None

        cursor.execute(
            "INSERT INTO users(user_id,ref) VALUES(?,?)",
            (user_id, ref)
        )

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

# ================= CHECK SUB =================

@dp.callback_query_handler(lambda c: c.data == "checksub")
async def checksub(call: types.CallbackQuery):

    if await check_sub(call.from_user.id):
        await bot.send_message(call.from_user.id, "✅ Verified", reply_markup=menu)
    else:
        await bot.answer_callback_query(call.id, "❌ Not joined", show_alert=True)

# ================= BALANCE =================

@dp.message_handler(lambda m: m.text == "💰 Balance")
async def balance(message: types.Message):

    cursor.execute(
        "SELECT points FROM users WHERE user_id=?",
        (message.from_user.id,)
    )

    data = cursor.fetchone()
    points = data[0] if data else 0

    await message.answer(f"💰 Points: {points}")

# ================= GIVEAWAY =================

@dp.message_handler(lambda m: m.text == "🎁 Giveaway")
async def giveaway(message: types.Message):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("⭐ Telegram Stars", callback_data="reward_15")
    )

    kb.add(
        InlineKeyboardButton("🎁 Gift Card", callback_data="reward_30")
    )

    kb.add(
        InlineKeyboardButton("📱 Airtime", callback_data="reward_20")
    )

    await message.answer("Choose reward", reply_markup=kb)

# ================= REWARD REQUEST =================

@dp.callback_query_handler(lambda c: c.data.startswith("reward_"))
async def reward(call: types.CallbackQuery):

    user_id = call.from_user.id
    amount = int(call.data.split("_")[1])

    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    points = cursor.fetchone()[0]

    if points < amount:
        await bot.answer_callback_query(call.id, "❌ Not enough points", show_alert=True)
        return

    cursor.execute(
        "UPDATE users SET points=points-? WHERE user_id=?",
        (amount, user_id)
    )

    conn.commit()

    await bot.send_message(
        ADMIN_ID,
        f"""
🎁 Reward Request
User: {user_id}
Points Used: {amount}
"""
    )

    await bot.send_message(user_id, "⏳ Request sent to admin")

# ================= REDEEM CODE =================

@dp.message_handler(commands=["redeem"])
async def redeem(message: types.Message):

    code = message.get_args()

    cursor.execute(
        "SELECT reward FROM redeem_codes WHERE code=?",
        (code,)
    )

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

# ================= ADMIN COMMANDS =================

@dp.message_handler(commands=["stats"])
async def stats(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    await message.answer(f"""
📊 Bot Stats
Users: {users}
""")

@dp.message_handler(commands=["givepoints"])
async def givepoints(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, uid, pts = message.text.split()
        uid = int(uid)
        pts = int(pts)

        cursor.execute(
            "UPDATE users SET points=points+? WHERE user_id=?",
            (pts, uid)
        )

        conn.commit()

        await message.answer("✅ Points given")

    except:
        await message.answer("Usage: /givepoints user_id points")

@dp.message_handler(commands=["redeemcreate"])
async def create_redeem(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, code, reward = message.text.split()

        cursor.execute(
            "INSERT INTO redeem_codes VALUES(?,?)",
            (code, int(reward))
        )

        conn.commit()

        await message.answer("✅ Redeem code created")

    except:
        await message.answer("Usage: /redeemcreate code reward")

# ================= RUN =================

import asyncio

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
