import os
import time
from threading import Thread
from flask import Flask
import asyncio
from telegram.ext import Application

# ========== FLASK ДЛЯ RENDER ==========
web_app = Flask(__name__)
port = int(os.environ.get("PORT", 10000))

@web_app.route('/')
def home():
    return "🤖 Бот работает!"

@web_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== ЗАПУСК FLASK ==========
print("🌐 Запуск Flask...")
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(2)
print("✅ Flask запущен")

# ========== ПРОВЕРКА ТОКЕНА ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# ========== ПРОСТОЙ БОТ ДЛЯ ТЕСТА ==========
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Простая команда /start
    from telegram import Update
    from telegram.ext import CommandHandler, ContextTypes
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("✅ Бот работает на Render!")
    
    app.add_handler(CommandHandler("start", start))
    
    print("🤖 Бот инициализирован")
    print("📡 Ожидание сообщений...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
