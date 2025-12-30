import os
import asyncio
import threading
from flask import Flask
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

print("=" * 50)
print("🤖 БОТ С ИСПРАВЛЕННЫМ EVENT LOOP")
print("=" * 50)

# 1. Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# 2. Flask в отдельном потоке с СВОИМ event loop
def run_flask():
    """Запускает Flask в отдельном потоке"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "🤖 Бот работает! Напиши /start в Telegram"
    
    @app.route('/health')
    def health():
        return "OK", 200
    
    @app.route('/debug')
    def debug():
        return f"Bot running with token: {BOT_TOKEN[:10]}..."
    
    print("[FLASK] Запускаю сервер...")
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# Запускаем Flask в отдельном потоке
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

import time
time.sleep(3)  # Даём время Flask запуститься
print("🌐 Flask запущен на порту 10000")

# 3. Команды бота
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📨 Получена команда /start от {update.effective_user.id}")
    await update.message.reply_text(
        f"✅ Привет, {update.effective_user.first_name}!\n"
        f"Бот работает на Render!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Помощь: /start, /help, /ping")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    await update.message.reply_text(f"🏓 Pong! Время: {now}")

# 4. Главная функция для Telegram бота
def run_telegram_bot():
    """Запускает Telegram бота в основном потоке"""
    print("🔄 Создаю Application для Telegram...")
    
    async def main():
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping_command))
        
        print("✅ Telegram бот инициализирован")
        print("📡 Ожидание сообщений...")
        print("👉 Напиши боту /start в Telegram")
        
        await application.run_polling()
    
    # Создаём новый event loop для Telegram бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    finally:
        loop.close()

# 5. Запуск всего
if __name__ == "__main__":
    run_telegram_bot()
