import os
import asyncio
import time
from threading import Thread
from flask import Flask
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

print("=" * 50)
print("🤖 БОТ С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ")
print("=" * 50)

# 1. Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# 2. Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот работает! Напиши /start в Telegram"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/debug')
def debug():
    return f"""
    <h1>Debug Info</h1>
    <p>Bot Token: {BOT_TOKEN[:10]}...</p>
    <p>Status: Running</p>
    <p><a href='/health'>Health Check</a></p>
    """

Thread(target=lambda: app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False), daemon=True).start()
time.sleep(3)
print("🌐 Flask запущен на порту 10000")

# 3. Команды бота
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📨 Получена команда /start от {update.effective_user.id}")
    await update.message.reply_text(
        f"✅ Привет, {update.effective_user.first_name}!\n"
        f"Бот работает на Render.\n"
        f"Твой ID: {update.effective_user.id}"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Помощь: /start, /help, /ping")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    await update.message.reply_text(f"🏓 Pong! Серверное время: {now}")

# 4. Главная функция
async def main():
    print("🔄 Создаю Application...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    print("📝 Регистрирую команды...")
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping_command))
    
    print("✅ Бот полностью инициализирован")
    print("📡 Ожидание сообщений в Telegram...")
    print("👉 Напиши боту /start")
    
    await application.run_polling()

# 5. Запуск
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
