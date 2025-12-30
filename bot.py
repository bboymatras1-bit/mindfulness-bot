# mindfulness_bot_v5.py
# Python 3.11 | python-telegram-bot v20+

import os
import json
import time
import threading
from datetime import datetime, date
from typing import Dict, Any

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

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ Переменная окружения BOT_TOKEN не установлена")

START_HOUR = 9
END_HOUR = 21
POLL_INTERVAL = 7200  # 2 часа
DATA_FILE = "user_data.json"

# ================== ГЛОБАЛЬНЫЕ ДАННЫЕ ==================

active_users: set[int] = set()
user_states: Dict[int, Dict[str, Any]] = {}
user_data: Dict[str, Any] = {}

bot_app: Application | None = None
stop_timer = False

# ================== КЛАВИАТУРЫ ==================

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

# ================== ХРАНЕНИЕ ДАННЫХ ==================

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

    user_data.setdefault(uid, {
        "first_name": "",
        "records": {}
    })

    user_data[uid]["records"].setdefault(today, [])
    record["timestamp"] = datetime.now().isoformat()
    user_data[uid]["records"][today].append(record)
    save_user_data()

# ================== ВРЕМЯ ==================

def is_active_time() -> bool:
    h = datetime.now().hour
    return START_HOUR <= h < END_HOUR

def next_poll_time() -> datetime:
    now = datetime.now()
    if not is_active_time():
        return now.replace(
            hour=START_HOUR, minute=0, second=0, microsecond=0
        ) + (now.hour >= END_HOUR) * timedelta(days=1)

    seconds = ((now.hour - START_HOUR) * 3600 +
               now.minute * 60 + now.second)
    next_sec = ((seconds // POLL_INTERVAL) + 1) * POLL_INTERVAL

    hour = START_HOUR + next_sec // 3600
    minute = (next_sec % 3600) // 60

    if hour >= END_HOUR:
        return now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0) + timedelta(days=1)

    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

# ================== ОТПРАВКА ОПРОСА ==================

def send_poll(user_id: int):
    if not bot_app:
        return

    username = user_data.get(str(user_id), {}).get("first_name", "друг")

    text = (
        f"🕰 *Время самопроверки, {username}!*\n\n"
        f"*1. В каком состоянии внимание?*"
    )

    user_states[user_id] = {"step": 1, "data": {}}

    async def _send():
        await bot_app.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=state_keyboard
        )

    bot_app.create_task(_send())

# ================== ТАЙМЕР ==================

def poll_timer():
    global stop_timer
    last_minute = None

    while not stop_timer:
        now = datetime.now()

        if is_active_time():
            if now.minute % (POLL_INTERVAL // 60) == 0:
                if last_minute != now.minute:
                    for uid in list(active_users):
                        send_poll(uid)
                    last_minute = now.minute
        else:
            last_minute = None

        time.sleep(30)

# ================== HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_app

    user = update.effective_user
    uid = user.id

    bot_app = context.application
    active_users.add(uid)

    user_data.setdefault(str(uid), {
        "first_name": user.first_name or "",
        "records": {}
    })
    save_user_data()

    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"✅ Ты подписан на опросы осознанности\n"
        f"⏰ Время: {START_HOUR}:00–{END_HOUR}:00\n"
        f"🔁 Интервал: {POLL_INTERVAL//3600} часа\n\n"
        f"Команды:\n"
        f"/stats — статистика\n"
        f"/stop — отписаться",
        parse_mode="Markdown"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_users.discard(update.effective_user.id)
    await update.message.reply_text("🛑 Ты отписался от опросов")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    today = date.today().isoformat()

    records = user_data.get(uid, {}).get("records", {}).get(today)
    if not records:
        await update.message.reply_text("📊 Сегодня записей нет")
        return

    total = len(records)
    present = sum(1 for r in records if r["state"].startswith("👁️"))
    minutes = sum(r.get("minutes", 0) for r in records)

    await update.message.reply_text(
        f"📊 *Статистика за сегодня*\n\n"
        f"• Опросов: {total}\n"
        f"• Присутствие: {present}\n"
        f"• Минут на цель: {minutes}",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in user_states:
        return

    step = user_states[uid]["step"]
    text = update.message.text

    if step == 1:
        user_states[uid]["data"]["state"] = text
        user_states[uid]["step"] = 2
        await update.message.reply_text(
            "💬 Хочешь добавить комментарий?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("➡️ Пропустить комментарий")]],
                resize_keyboard=True
            )
        )
        return

    if step == 2:
        user_states[uid]["data"]["state_comment"] = "" if "Пропустить" in text else text
        user_states[uid]["step"] = 3
        await update.message.reply_text(
            "🎯 Помнил ли о цели?",
            reply_markup=goal_keyboard
        )
        return

    if step == 3:
        user_states[uid]["data"]["remembered_goal"] = text
        user_states[uid]["step"] = 4
        await update.message.reply_text("⏱ Сколько минут уделил цели?")
        return

    if step == 4:
        try:
            minutes = int(text)
        except ValueError:
            await update.message.reply_text("Введи число")
            return

        user_states[uid]["data"]["minutes"] = minutes
        add_record(uid, user_states[uid]["data"])
        del user_states[uid]

        await update.message.reply_text("✅ Запись сохранена!")

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

    timer = threading.Thread(target=poll_timer, daemon=True)
    timer.start()

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
