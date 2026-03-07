import os
import logging
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# ================= CONFIG =================

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7334992081"))

CHANNELS = [
    "@HackingToolshere",
    "@CYBERNOVA0"
]

REF_REWARD = 2   # ⭐ Referral reward changed to 2 points

# Giveaway cost
PRIZES = {
    "netflix": 20,
    "whatsapp": 15
}

# ================= INIT =================

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
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
CREATE TABLE IF NOT EXISTS used_ref(
user_id INTEGER PRIMARY KEY
)
""")

conn.commit()

# ================= MENUS =================

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Balance"), KeyboardButton(text="🎁 Giveaway")],
        [KeyboardButton(text="👥 Referral")]
    ],
    resize_keyboard=True
)

# ================= HELPERS =================

async def check_sub(user_id: int):
    try:
        for channel in CHANNELS:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == "left":
                return False
        return True
    except:
        return False

def join_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channels", url="https://t.me/HackingToolshere")],
            [InlineKeyboardButton(text="✅ Check", callback_data="checksub")]
        ]
    )

# ================= START =================

@dp.message(lambda m: m.text.startswith("/start"))
async def start(message: types.Message):

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

        cursor.execute("INSERT INTO users(user_id,ref) VALUES(?,?)", (user_id, ref))
        conn.commit()

        # Referral reward (2 points only)
        if ref:
            cursor.execute("SELECT * FROM used_ref WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("UPDATE users SET points=points+? WHERE user_id=?", (REF_REWARD, ref))
                cursor.execute("INSERT INTO used_ref(user_id) VALUES(?)", (user_id,))
                conn.commit()

    if not await check_sub(user_id):
        await message.answer("❌ Join channels first", reply_markup=join_kb())
        return

    await message.answer("🎉 Welcome Giveaway Bot", reply_markup=menu)

# ================= CHECK SUB =================

@dp.callback_query(lambda c: c.data == "checksub")
async def checksub(call: types.CallbackQuery):

    if await check_sub(call.from_user.id):
        await call.message.answer("✅ Verified", reply_markup=menu)
    else:
        await call.answer("❌ Not joined", show_alert=True)

# ================= BALANCE =================

@dp.message(lambda m: m.text == "💰 Balance")
async def balance(message: types.Message):

    cursor.execute("SELECT points FROM users WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchone()

    points = data[0] if data else 0
    await message.answer(f"💰 Points: {points}")

# ================= REFERRAL =================

@dp.message(lambda m: m.text == "👥 Referral")
async def referral(message: types.Message):

    link = f"https://t.me/{(await bot.me()).username}?start={message.from_user.id}"

    await message.answer(f"""
👥 Referral System

Your link:
{link}

🎁 Earn {REF_REWARD} points per referral
""")

# ================= GIVEAWAY =================

@dp.message(lambda m: m.text == "🎁 Giveaway")
async def giveaway(message: types.Message):

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Netflix Account", callback_data="prize_netflix")],
            [InlineKeyboardButton(text="📱 WhatsApp Number", callback_data="prize_whatsapp")]
        ]
    )

    await message.answer("🎁 Choose prize (Request will be sent to admin)", reply_markup=kb)

# ================= PRIZE REQUEST =================

@dp.callback_query(lambda c: c.data.startswith("prize_"))
async def prize_request(call: types.CallbackQuery):

    user_id = call.from_user.id
    prize = call.data.split("_")[1]

    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    points = data[0] if data else 0

    cost = PRIZES.get(prize, 0)

    if points < cost:
        await call.answer("❌ Not enough points", show_alert=True)
        return

    cursor.execute(
        "UPDATE users SET points=points-? WHERE user_id=?",
        (cost, user_id)
    )
    conn.commit()

    # Send request to admin
    await bot.send_message(
        ADMIN_ID,
        f"""
🎁 Prize Request

User: {user_id}
Prize: {prize}
Cost Points: {cost}
"""
    )

    await bot.send_message(user_id, "⏳ Request sent to admin. Wait for prize delivery.")

# ================= RUN =================

async def main():
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
