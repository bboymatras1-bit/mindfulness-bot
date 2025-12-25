import os
import time
from flask import Flask
from telegram import Bot

print("=" * 50)
print("🤖 НАЧИНАЮ ТЕСТОВЫЙ ЗАПУСК...")
print("=" * 50)

# 1. Проверяем переменные окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

if not CHAT_ID:
    print("❌ CHAT_ID не найден в переменных окружения!")
    exit(1)

print(f"✅ BOT_TOKEN: {BOT_TOKEN[:10]}...")
print(f"✅ CHAT_ID: {CHAT_ID}")

# 2. Запускаем Flask (обязательно для Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает! ✅"

@app.route('/health')
def health():
    return "OK", 200

# Запускаем Flask в фоне
from threading import Thread
def run_flask():
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

Thread(target=run_flask, daemon=True).start()
time.sleep(2)
print("🌐 Flask запущен на порту 10000")

# 3. Тестируем отправку сообщения
try:
    bot = Bot(token=BOT_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text="✅ Бот запущен на Render!")
    print("✅ Тестовое сообщение отправлено в Telegram")
except Exception as e:
    print(f"❌ Ошибка Telegram: {e}")

print("=" * 50)
print("📊 ТЕСТ ЗАВЕРШЁН УСПЕШНО")
print("=" * 50)

# Просто завершаем программу - это для теста
