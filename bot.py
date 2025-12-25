import os
import time
import threading
import schedule
from datetime import datetime
from flask import Flask
from telegram import Bot

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('8424450945:AAE6uWv4tlADMTfH-rUNojYEIUVqwTei9JY')
PORT = int(os.environ.get('PORT', 10000))

# ========== FLASK ДЛЯ RENDER ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот-Криветка работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# ========== ОСНОВНАЯ ЛОГИКА ==========
def send_message():
    try:
        bot = Bot(token=BOT_TOKEN)
        current_time = datetime.now().strftime("%H:%M:%S")
        bot.send_message(chat_id=CHAT_ID, text=f"🦐 Привет Криветка! {current_time}")
        print(f"✅ Отправлено в {current_time}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def run_scheduler():
    schedule.every(1).minutes.do(send_message)
    send_message()  # Первое сообщение сразу
    print("⏰ Планировщик запущен")
    while True:
        schedule.run_pending()
        time.sleep(1)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🤖 Запуск бота...")
    
    # Проверка токена и chat_id
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Задай BOT_TOKEN и CHAT_ID в настройках Render!")
        exit(1)
    
    # Запуск Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)
    print(f"🌐 Flask запущен на порту {PORT}")
    
    # Запуск планировщика
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("✅ Бот готов. Сообщения каждую минуту.")
    
    # Держим программу активной
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Остановка")
