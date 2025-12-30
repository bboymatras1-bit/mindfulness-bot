# mindfulness_bot_v5_fixed.py
# Python 3.11 | python-telegram-bot v20+

import os
import json
import time
import threading
from datetime import datetime, date, timedelta
from typing import Dict, Any

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ Переменная окружения BOT_TOKEN не установлена")

START_HOUR = 9
END_HOUR = 21
POLL_INTERVAL = timedelta(hours=2)
DATA_FILE = "user_data.json"

# ================== ДАННЫЕ ==================

active_users: set[int] = set()
user_states: Dict[int, Dict[str, Any]] = {}
user_data: Dict[str, Any] = {}

bot_app: Application | None = None
stop_timer = False
last_poll_time: datetime | None = None

# ================== КЛАВИАТУРЫ ==================

state_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("👁️ Был внимателен и присутствовал")],
        [KeyboardButton("🤖 Спал и действовал на автомате")],
    ],
    resize_keyboard=True,
)

goal_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("✅ Да"), KeyboardButton("❌ Нет")],
    ],
    resize_keyboard=True,
)

# ================== ХРАНЕНИЕ ==================

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
    uid = str(user_id)
    today = date.today().isoformat()

    user_data.setdefault(uid, {"records": {}})
    user_data[uid]["records"].setdefault(today, [])

    record["timestamp"] = datetime.now().isoformat()
    user_data[uid]["records"][today].append(record)
    save_user_data()

# ================== ВРЕМЯ ==================

def is_active_time() -> bool:
    h = datetime.now().hour
    return START_HOUR <= h < END_HOUR

# ================== ОПРОС ==================

def send_poll(user_id: int):
    if not bot_app:
        return

    user_states[user_id] = {"step": 1, "data": {}}

    async def _send():
        await bot_app.bot.send_message(
            chat_id=user_id,
            text="🕰 *Самопроверка*\n\nВ каком состоянии внимание?",
            parse_mode="Markdown",
            reply_markup=state_keyboard
        )

    bot_app.bot.loop.create_task(_send())

# ================== ТАЙМЕР ==================

def poll_timer():
    global last_poll_time

    while not stop_timer:
        now = datetime.now()

        if is_active_time():
            if not last_poll_time or now - last_poll_time >= POLL_INTERVAL:
                for uid in list(active_users):
                    send_poll(uid)
                last_poll_time = now

        time.sleep(30)

# ================== HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    active_users.add(uid)

    user_data.setdefault(str(uid), {"records": {}})
    save_user_data()

    await update.message.reply_text(
        "👋 Ты подписан на опросы осознанности\n"
        "⏰ 09:00–21:00 | каждые 2 часа\n\n"
        "/stats — статистика\n"
        "/stop — отписаться"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_users.discard(update.effective_user.id)
    await update.message.reply_text("🛑 Опросы остановлены")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    today = date.today().isoformat()

    records = user_data.get(uid, {}).get("records", {}).get(today, [])
    await update.message.reply_text(f"📊 Записей сегодня: {len(records)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if uid not in user_states:
        return

    step = user_states[uid]["step"]

    if step == 1:
        user_states[uid]["data"]["state"] = text
        user_states[uid]["step"] = 2
        await update.message.reply_text("⏱ Сколько минут уделил цели?")
        return

    if step == 2:
        try:
            minutes = int(text)
        except ValueError:
            await update.message.reply_text("Введите число")
            return

        user_states[uid]["data"]["minutes"] = minutes
        add_record(uid, user_states[uid]["data"])
        del user_states[uid]

        await update.message.reply_text("✅ Сохранено")

# ================== MAIN ==================

def main():
    global bot_app

    load_user_data()

    app = Application.builder().token(BOT_TOKEN).build()
    bot_app = app

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    threading.Thread(target=poll_timer, daemon=True).start()

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
