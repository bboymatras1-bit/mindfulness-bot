import os
import time
import threading
import schedule
from datetime import datetime
from flask import Flask
from telegram import Bot
from telegram.error import TelegramError

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('8424450945:AAE6uWv4tlADMTfH-rUNojYEIUVqwTei9JY')  # ID твоего чата с ботом
PORT = int(os.environ.get('PORT', 10000))

if not BOT_TOKEN or not CHAT_ID:
    print("❌ ОШИБКА: Нужно задать BOT_TOKEN и CHAT_ID в настройках Render!")
    exit(1)

# ========== FLASK ДЛЯ RENDER ==========
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <h1>🤖 Бот-Криветка работает!</h1>
    <p>Отправляет "Привет Криветка" каждую минуту.</p>
    <p><a href='/health'>Проверка здоровья</a></p>
    <p><a href='/send-test'>Отправить тестовое сообщение</a></p>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/send-test')
def send_test():
    try:
        bot = Bot(token=BOT_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text="🔄 Тестовое сообщение от веб-интерфейса!")
        return "✅ Тестовое сообщение отправлено!"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}", 500

def run_flask():
    """Запуск Flask сервера"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# ========== ОСНОВНАЯ ЛОГИКА БОТА ==========
def send_crivetka_message():
    """Отправляет сообщение в Telegram"""
    try:
        bot = Bot(token=BOT_TOKEN)
        current_time = datetime.now().strftime("%H:%M:%S")
        message = f"🦐 Привет Криветка!\nВремя: {current_time}"
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"✅ Сообщение отправлено в {current_time}")
    except TelegramError as e:
        print(f"❌ Ошибка Telegram: {e}")
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")

def run_scheduler():
    """Запускает планировщик для отправки сообщений"""
    # Отправляем каждую минуту
    schedule.every(1).minutes.do(send_crivetka_message)
    
    # Отправляем первое сообщение сразу
    print("🚀 Первый запуск...")
    send_crivetka_message()
    
    print("⏰ Планировщик запущен. Сообщения каждую минуту.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# ========== ЗАПУСК ==========
def main():
    print("=" * 50)
    print("🤖 БОТ-КРИВЕТКА")
    print("=" * 50)
    print(f"Токен: {BOT_TOKEN[:10]}...")
    print(f"Чат ID: {CHAT_ID}")
    print(f"Порт: {PORT}")
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Flask запущен на порту {PORT}")
    
    # Ждем немного для инициализации Flask
    time.sleep(2)
    
    # Запускаем планировщик
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ Все компоненты запущены")
    print("⏳ Ожидание сообщений...")
    
    # Держим основной поток активным
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")

if __name__ == "__main__":
    main()

