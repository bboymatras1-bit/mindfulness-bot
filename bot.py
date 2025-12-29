import os
import time
import threading
from datetime import datetime
from flask import Flask
from telegram import Bot

# ========== 1. ПОЛУЧАЕМ НАСТРОЙКИ ==========
# Токен и Chat ID берутся ТОЛЬКО из переменных окружения Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')


# Проверяем, что настройки есть
if not BOT_TOKEN:
    print("❌ ОШИБКА: Переменная BOT_TOKEN не найдена!")
    print("   Добавь её в Render: Environment -> Add Environment Variable")
    print("   Key: BOT_TOKEN, Value: твой_токен_бота")
    exit(1)

print("=" * 50)
print("🤖 БОТ 'ПРИВЕТ КРИВЕТКА'")
print("=" * 50)
print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")
print(f"✅ Чат ID: {CHAT_ID}")

# ========== 2. FLASK ДЛЯ RENDER ==========
# Render требует открытый порт, поэтому нужен Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот работает! <a href='/health'>/health</a>"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускаем Flask сервер на порту 10000"""
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# Запускаем Flask в фоновом потоке
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(2)  # Даём время Flask запуститься
print("🌐 Flask сервер запущен на порту 10000")

# ========== 3. ОСНОВНАЯ ЛОГИКА БОТА ==========
def send_message():
    """Отправляет 'Привет Криветка' в Telegram"""
    try:
        bot = Bot(token=BOT_TOKEN)
        current_time = datetime.now().strftime("%H:%M:%S")
        message = f"🦐 Привет Криветка!\nВремя: {current_time}"
        
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"✅ Отправлено в {current_time}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def message_loop():
    """Бесконечный цикл отправки каждую минуту"""
    print("⏰ Запуск цикла сообщений...")
    
    # Отправляем первое сообщение сразу
    send_message()
    
    # Затем каждые 60 секунд
    while True:
        time.sleep(60)
        send_message()

# ========== 4. ЗАПУСК ВСЕГО ==========
if __name__ == "__main__":
    # Запускаем отправку сообщений в отдельном потоке
    bot_thread = threading.Thread(target=message_loop, daemon=True)
    bot_thread.start()
    
    print("✅ Бот запущен. Сообщения каждую минуту.")
    print("⚙️ Чтобы остановить: Ctrl+C в логах Render")
    
    # Держим основной поток активным
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")

