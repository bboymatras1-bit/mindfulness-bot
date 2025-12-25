import os
import time
import threading
from datetime import datetime
from flask import Flask
from telegram import Bot

# ========== ПОЛУЧАЕМ ТОКЕН ТОЛЬКО ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
PORT = int(os.environ.get('PORT', 10000))

# КРИТИЧЕСКАЯ ПРОВЕРКА - если нет токена, бот не запустится
if not BOT_TOKEN:
    print("❌ ОШИБКА: Переменная окружения BOT_TOKEN не найдена!")
    print("   Добавь её в настройках Render: Environment -> Add Environment Variable")
    print("   Key: BOT_TOKEN")
    print("   Value: твой_токен_бота")
    exit(1)

if not CHAT_ID:
    print("❌ ОШИБКА: Переменная окружения CHAT_ID не найдена!")
    print("   Добавь её в настройках Render")
    print("   Key: CHAT_ID")
    print("   Value: твой_chat_id (получи в @userinfobot)")
    exit(1)

print("=" * 50)
print("🤖 БОТ-КРИВЕТКА")
print("=" * 50)
print(f"✅ Токен загружен: {BOT_TOKEN[:10]}...")
print(f"✅ Чат ID: {CHAT_ID}")
print(f"✅ Порт: {PORT}")

# ========== FLASK ДЛЯ RENDER (ОБЯЗАТЕЛЬНО) ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот работает на Render! <a href='/health'>/health</a>"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускает Flask сервер (нужен Render для проверки порта)"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# ========== ОСНОВНАЯ ЛОГИКА БОТА ==========
def send_crivetka():
    """Отправляет 'Привет Криветка' в Telegram"""
    try:
        bot = Bot(token=BOT_TOKEN)
        now = datetime.now().strftime("%H:%M:%S")
        message = f"🦐 Привет Криветка!\nВремя: {now}"
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"✅ Сообщение отправлено в {now}")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")

def message_loop():
    """Бесконечный цикл - отправка каждую минуту"""
    print("⏰ Запуск цикла сообщений...")
    
    # Отправляем первое сообщение сразу
    send_crivetka()
    
    # Затем каждые 60 секунд
    while True:
        time.sleep(60)
        send_crivetka()

# ========== ЗАПУСК ВСЕГО ==========
if __name__ == "__main__":
    # 1. Запускаем Flask в отдельном потоке (для Render)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)  # Даем Flask время запуститься
    print(f"🌐 Flask сервер запущен на порту {PORT}")
    
    # 2. Запускаем бота, который отправляет сообщения
    bot_thread = threading.Thread(target=message_loop, daemon=True)
    bot_thread.start()
    
    print("✅ Все компоненты запущены")
    print("🔄 Сообщения будут отправляться каждую минуту...")
    
    # 3. Держим основной поток активным
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
