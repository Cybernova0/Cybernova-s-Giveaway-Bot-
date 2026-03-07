import os
import logging
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command, Text

# ================= CONFIG =================

TOKEN = os.environ.get("BOT_TOKEN")

if TOKEN is None:
    raise Exception("BOT_TOKEN not set in environment variables")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "7334992081"))

CHANNELS = [
    "@HackingToolshere",
    "@CYBERNOVA0"
]

# ================= INIT =================

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=types.bot_command.BotCommandScopeDefault()
)

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

# ================= KEYBOARDS =================

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Balance"), KeyboardButton(text="🎁 Giveaway")],
        [KeyboardButton(text="👥 Referral"), KeyboardButton(text="🏆 Leaderboard")]
    ],
    resize_keyboard=True
)

def join_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Join Channels",
            url="https://t.me/HackingToolshere"
        )],
        [InlineKeyboardButton(
            text="✅ Check",
            callback_data="checksub"
        )]
    ])
    return kb

# ================= HELPERS =================

async def check_sub(user_id):
    try:
        for channel in CHANNELS:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == "left":
                return False
        return True
    except:
        return False

# ================= HANDLERS =================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref = None
        if len(args) > 1 and args[1].isdigit():
            ref = int(args[1])

        if ref == user_id:
            ref = None

        cursor.execute(
            "INSERT INTO users(user_id, ref) VALUES(?,?)",
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
        await message.answer("❌ Please join channels first", reply_markup=join_kb())
        return

    await message.answer("🎉 Welcome Giveaway Bot", reply_markup=menu)

# ================= CALLBACK =================

@dp.callback_query(Text("checksub"))
async def check_sub_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.answer("✅ Verified", reply_markup=menu)
    else:
        await call.answer("❌ Not joined", show_alert=True)

# ================= BALANCE =================

@dp.message(Text("💰 Balance"))
async def balance_handler(message: types.Message):
    cursor.execute(
        "SELECT points FROM users WHERE user_id=?",
        (message.from_user.id,)
    )

    data = cursor.fetchone()
    points = data[0] if data else 0

    await message.answer(f"💰 Points: {points}")

# ================= GIVEAWAY =================

@dp.message(Text("🎁 Giveaway"))
async def giveaway_handler(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="reward_15")],
        [InlineKeyboardButton(text="🎁 Gift Card", callback_data="reward_30")],
        [InlineKeyboardButton(text="📱 Airtime", callback_data="reward_20")]
    ])

    await message.answer("Choose reward", reply_markup=kb)

# ================= REWARD =================

@dp.callback_query(Text(startswith="reward_"))
async def reward_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    amount = int(call.data.split("_")[1])

    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    if not data or data[0] < amount:
        await call.answer("❌ Not enough points", show_alert=True)
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

    await call.message.answer("⏳ Request sent to admin")

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
