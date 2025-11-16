import logging
import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://happy-heart.up.railway.app{WEBHOOK_PATH}"

# Aiogram bot va dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FastAPI app
app = FastAPI()

# DB konfiguratsiyasi
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

# DB bilan ishlash funksiyalari
def connect_db():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        cursor_factory=RealDictCursor
    )

def get_messages(offset=0, limit=5):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, number, message FROM general_messages ORDER BY id DESC OFFSET %s LIMIT %s",
        (offset, limit)
    )
    data = cur.fetchall()
    conn.close()
    return data

def get_total_count():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM general_messages")
    total = cur.fetchone()['count']
    conn.close()
    return total

def delete_by_id(msg_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM general_messages WHERE id = %s", (msg_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

# States
class DeleteClient(StatesGroup):
    number = State()

user_pages = {}

# Logging
logging.basicConfig(level=logging.INFO)

# START COMMAND
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Assalomu alaykum!\n"
        "📋 Clientlarni ko‘rish uchun: 📋 Clientlar\n"
        "❌ Clientni o‘chirish uchun: Delete"
    )

# SHOW CLIENTS
@dp.message(lambda m: m.text and m.text.strip() == "📋 Clientlar")
async def show_clients(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user_pages[user_id] = 0

    users = get_messages(offset=0)
    total = get_total_count()

    if users:
        text = "📋 Foydalanuvchilar (1-sahifa):\n\n"
        for u in users:
            text += f"🆔 {u['id']} | 👤 {u['name']} | 📞 {u['number']} | ✉ {u['message']}\n"

        buttons = []
        if total > 5:
            buttons.append([types.InlineKeyboardButton(text="➡️ Keyingi", callback_data="next_page")])

        kb = types.InlineKeyboardMarkup(inline_keyboard=buttons if buttons else [])
        await message.answer(text, reply_markup=kb)
    else:
        await message.answer("Foydalanuvchilar topilmadi.")

# DELETE CLIENT
@dp.message(lambda m: m.text and m.text.strip() == "❌ Clientni o'chirish")
async def ask_delete(message: types.Message, state: FSMContext):
    await message.answer("Qaysi clientni o‘chirmoqchisiz? Iltimos ID kiriting:")
    await state.set_state(DeleteClient.number)

@dp.message(DeleteClient.number)
async def confirm_delete(message: types.Message, state: FSMContext):
    client_id = message.text.strip()
    if not client_id.isdigit():
        await message.answer("ID faqat raqam bo‘lishi kerak!")
        return

    deleted = delete_by_id(int(client_id))
    if deleted:
        await message.answer(f"Client (ID: {client_id}) muvaffaqiyatli o‘chirildi ✔")
    else:
        await message.answer(f"Bunday ID mavjud emas ❌")
    await state.clear()

# PAGINATION CALLBACKS
def create_pagination_keyboard(offset, total):
    buttons = []
    row = []
    if offset >= 5:
        row.append(types.InlineKeyboardButton(text="⬅️ Oldingi", callback_data="prev_page"))
    if total > offset + 5:
        row.append(types.InlineKeyboardButton(text="➡️ Keyingi", callback_data="next_page"))
    if row:
        buttons.append(row)
    return types.InlineKeyboardMarkup(inline_keyboard=buttons if buttons else [])

@dp.callback_query(lambda c: c.data == "next_page")
async def next_page(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_pages[user_id] += 5
    offset = user_pages[user_id]
    users = get_messages(offset=offset)
    total = get_total_count()

    if not users:
        await callback.answer("Boshqa foydalanuvchilar yo‘q.")
        return

    page = offset // 5 + 1
    text = f"📋 Foydalanuvchilar ({page}-sahifa):\n\n"
    for u in users:
        text += f"🆔 {u['id']} | 👤 {u['name']} | 📞 {u['number']} | ✉ {u['message']}\n"

    kb = create_pagination_keyboard(offset, total)
    await callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "prev_page")
async def prev_page(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_pages[user_id] = max(user_pages[user_id] - 5, 0)
    offset = user_pages[user_id]
    users = get_messages(offset=offset)
    total = get_total_count()

    page = offset // 5 + 1
    text = f"📋 Foydalanuvchilar ({page}-sahifa):\n\n"
    for u in users:
        text += f"🆔 {u['id']} | 👤 {u['name']} | 📞 {u['number']} | ✉ {u['message']}\n"

    kb = create_pagination_keyboard(offset, total)
    await callback.message.edit_text(text, reply_markup=kb)

# TELEGRAM WEBHOOK ENDPOINT
@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    update = types.Update(**await req.json())
    await dp.process_update(update)
    return {"ok": True}

# STARTUP & SHUTDOWN EVENTS
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

# RUN Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    