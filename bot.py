import os
import asyncio
import threading
import time
from flask import Flask
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

print("=" * 50)
print("🤖 БОТ: РАБОЧАЯ ВЕРСИЯ БЕЗ ОШИБОК EVENT LOOP")
print("=" * 50)

# 1. Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# 2. Flask в ОТДЕЛЬНОМ ПОТОКЕ (важно!)
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Бот работает! Напиши /start в Telegram"

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускает Flask в отдельном потоке"""
    print("[FLASK] Запускаю веб-сервер...")
    flask_app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# Запускаем Flask сразу в отдельном потоке
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(3)
print("🌐 Flask запущен на порту 10000")

# 3. Telegram бот (основной поток)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    print(f"📨 /start от {user.id} ({user.first_name})")
    await update.message.reply_text(
        f"✅ Привет, {user.first_name}!\n"
        f"Твой ID: {user.id}\n"
        f"Бот работает на Render!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Команды:\n/start - приветствие\n/help - помощь\n/ping - проверка")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    now = datetime.now().strftime("%H:%M:%S")
    await update.message.reply_text(f"🏓 Pong! Время сервера: {now}")

async def main_telegram():
    """Основная асинхронная функция для Telegram бота"""
    print("🔄 Инициализирую Telegram бота...")
    
    # Создаём Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping_command))
    
    print("✅ Telegram бот готов к работе")
    print("📱 Напиши боту /start в Telegram")
    
    # Запускаем polling
    await application.run_polling()

def run_telegram_bot():
    """Запускает Telegram бота в основном потоке"""
    try:
        # Создаём новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_telegram())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка в Telegram боте: {e}")
    finally:
        print("🔚 Завершение работы")

# 4. Точка входа
if __name__ == "__main__":
    print("🚀 Запуск основного потока бота...")
    run_telegram_bot()
