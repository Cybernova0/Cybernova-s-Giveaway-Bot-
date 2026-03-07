import os
import logging
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import *
from aiogram.client.default import DefaultBotProperties

# ================= CONFIG =================

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7334992081"))

CHANNELS = [
    "@HackingToolshere",
    "@CYBERNOVA0"
]

REF_REWARD = 2

PRIZE_COSTS = {
    "Netflix Acc": 50,
    "Whatsapp Number": 40,
    "Prime Video": 20
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS prize_requests(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
prize TEXT,
status TEXT DEFAULT 'pending'
)
""")

conn.commit()

# ================= MENU =================

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Balance"), KeyboardButton(text="🎁 Giveaway")],
        [KeyboardButton(text="👥 Referral"), KeyboardButton(text="👨‍💻 Contact Developer")],
        [KeyboardButton(text="📊 Admin Dashboard")]
    ],
    resize_keyboard=True
)

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

        cursor.execute(
            "INSERT INTO users(user_id,ref) VALUES(?,?)",
            (user_id, ref)
        )
        conn.commit()

        # Referral reward
        if ref:
            cursor.execute(
                "SELECT * FROM used_ref WHERE user_id=?",
                (user_id,)
            )

            if not cursor.fetchone():
                cursor.execute(
                    "UPDATE users SET points=points+? WHERE user_id=?",
                    (REF_REWARD, ref)
                )

                cursor.execute(
                    "INSERT INTO used_ref(user_id) VALUES(?)",
                    (user_id,)
                )

                conn.commit()

    if not await check_sub(user_id):
        await message.answer("❌ Join channels first", reply_markup=join_kb())
        return

    await message.answer("🎉 Welcome Giveaway Bot", reply_markup=menu)

# ================= CONTACT DEV =================

@dp.message(lambda m: m.text == "👨‍💻 Contact Developer")
async def contact_dev(message: types.Message):
    await message.answer("👨‍💻 Developer: @Cybernova_io")

# ================= REF =================

@dp.message(lambda m: m.text == "👥 Referral")
async def referral(message: types.Message):

    link = f"https://t.me/{(await bot.me()).username}?start={message.from_user.id}"

    await message.answer(
        f"""
👥 Referral System
Your Link:
{link}

Earn {REF_REWARD} points per referral
"""
    )

# ================= BALANCE =================

@dp.message(lambda m: m.text == "💰 Balance")
async def balance(message: types.Message):

    cursor.execute(
        "SELECT points FROM users WHERE user_id=?",
        (message.from_user.id,)
    )

    data = cursor.fetchone()
    points = data[0] if data else 0

    await message.answer(f"💰 Points: {points}")

# ================= GIVEAWAY =================

@dp.message(lambda m: m.text == "🎁 Giveaway")
async def giveaway(message: types.Message):

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🎬 Netflix ({PRIZE_COSTS['netflix']} pts)",
                                  callback_data="prize_netflix")],
            [InlineKeyboardButton(text=f"📱 WhatsApp ({PRIZE_COSTS['whatsapp']} pts)",
                                  callback_data="prize_whatsapp")],
            [InlineKeyboardButton(text=f"📞 Airtime ({PRIZE_COSTS['airtime']} pts)",
                                  callback_data="prize_airtime")]
        ]
    )

    await message.answer("🎁 Select Prize", reply_markup=kb)

# ================= PRIZE REQUEST =================

@dp.callback_query(lambda c: c.data.startswith("prize_"))
async def prize_request(call: types.CallbackQuery):

    user_id = call.from_user.id
    prize = call.data.split("_")[1]

    cost = PRIZE_COSTS[prize]

    cursor.execute(
        "SELECT points FROM users WHERE user_id=?",
        (user_id,)
    )

    data = cursor.fetchone()
    points = data[0] if data else 0

    if points < cost:
        await call.answer("❌ Not enough points", show_alert=True)
        return

    cursor.execute(
        "UPDATE users SET points=points-? WHERE user_id=?",
        (cost, user_id)
    )

    cursor.execute(
        "INSERT INTO prize_requests(user_id,prize) VALUES(?,?)",
        (user_id, prize)
    )

    conn.commit()

    await bot.send_message(
        ADMIN_ID,
        f"""
🎁 Prize Request
User: {user_id}
Prize: {prize}
"""
    )

    await call.message.answer("⏳ Request sent to admin")

# ================= ADMIN DASHBOARD =================

@dp.message(lambda m: m.text == "📊 Admin Dashboard")
async def admin_dashboard(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(points) FROM users")
    total_points = cursor.fetchone()[0] or 0

    text = f"""
👨‍💻 ADMIN PANEL

👥 Users: {users}
💰 Total Points: {total_points}
"""

    # Show pending requests
    cursor.execute(
        "SELECT id,user_id,prize FROM prize_requests WHERE status='pending'"
    )

    reqs = cursor.fetchall()

    if reqs:
        text += "\n📦 Pending Requests:\n"
        for r in reqs:
            text += f"{r[0]} | User {r[1]} | {r[2]}\n"

    await message.answer(text)

# ================= RUN =================

async def main():
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
