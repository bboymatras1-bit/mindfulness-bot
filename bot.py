import json
import os
from datetime import datetime, date, time as dt_time
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ← БЕЗОПАСНО
DATA_FILE = "user_data.json"

START_HOUR = 9
END_HOUR = 21
POLL_INTERVAL = 2 * 60 * 60  # 2 часа
# ============================================

active_users: set[int] = set()
user_states = {}
user_data = {}

# ---------- Keyboards ----------
state_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("👁️ Был внимателен и присутствовал")],
        [KeyboardButton("🤖 Спал и действовал на автомате")],
        [KeyboardButton("➡️ Пропустить комментарий")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

goal_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("✅ Да"), KeyboardButton("❌ Нет")],
        [KeyboardButton("➡️ Пропустить комментарий")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# ---------- Storage ----------
def load_user_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    else:
        user_data = {}

def save_user_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

def add_record(user_id: int, record: dict):
    today = date.today().isoformat()
    uid = str(user_id)

    user_data.setdefault(uid, {"records": {}})
    user_data[uid]["records"].setdefault(today, [])

    record["timestamp"] = datetime.now().isoformat()
    user_data[uid]["records"][today].append(record)
    save_user_data()

# ---------- Poll logic ----------
def is_active_time() -> bool:
    now = datetime.now().hour
    return START_HOUR <= now < END_HOUR

async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    if not is_active_time():
        return

    for user_id in list(active_users):
        user_states[user_id] = {"step": 1, "data": {}}
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🕰️ *Время самопроверки*\n\n"
                     "*1. В каком состоянии внимание?*",
                parse_mode="Markdown",
                reply_markup=state_keyboard,
            )
        except Exception:
            active_users.discard(user_id)

# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active_users.add(user_id)

    await update.message.reply_text(
        "👋 Ты подписан на опросы осознанности\n\n"
        f"⏰ {START_HOUR}:00 – {END_HOUR}:00\n"
        f"🔁 Каждые 2 часа",
        parse_mode="Markdown",
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_users.discard(update.effective_user.id)
    await update.message.reply_text("🛑 Ты отписался от опросов")

# ---------- Message handler ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_states:
        return

    step = user_states[user_id]["step"]
    text = update.message.text

    if step == 1:
        user_states[user_id]["data"]["state"] = text
        user_states[user_id]["step"] = 2
        await update.message.reply_text(
            "Помнил ли ты о цели?",
            reply_markup=goal_keyboard,
        )

    elif step == 2:
        user_states[user_id]["data"]["remembered_goal"] = text
        user_states[user_id]["step"] = 3
        await update.message.reply_text("Сколько минут уделил цели? (0–120)")

    elif step == 3:
        try:
            minutes = int(text)
            user_states[user_id]["data"]["minutes"] = minutes
            add_record(user_id, user_states[user_id]["data"])
            del user_states[user_id]

            await update.message.reply_text("✅ Запись сохранена")
        except ValueError:
            await update.message.reply_text("⚠️ Введи число")

# ---------- Main ----------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не задан")

    load_user_data()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ⏰ Планировщик
    app.job_queue.run_repeating(send_poll, interval=POLL_INTERVAL, first=10)

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
