import os
import time
from threading import Thread
from flask import Flask, request
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== 1. FLASK ДЛЯ RENDER (ОБЯЗАТЕЛЬНО) ==========
web_app = Flask(__name__)
port = int(os.environ.get("PORT", 10000))

@web_app.route('/')
def home():
    return "✅ Бот работает! <a href='/health'>Проверить</a>"

@web_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускаем Flask в отдельном потоке"""
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

print("🚀 Инициализация сервера...")
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(3)  # Даем время Flask запуститься
print("🌐 Flask сервер запущен на порту", port)

# ========== 2. ЗАГРУЗКА ТОКЕНА ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    print("   Добавь в настройках Render: Environment -> BOT_TOKEN")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# ========== 3. ОСНОВНОЙ КОД БОТА ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n"
        "✅ Бот работает на Render!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Команды:\n"
        "/start - приветствие\n"
        "/help - эта справка\n"
        "/status - проверка работы"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот активен и работает!")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    
    print("🤖 Бот инициализирован")
    print("📡 Ожидание сообщений...")
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
