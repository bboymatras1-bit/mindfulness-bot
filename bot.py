import os
import time
import asyncio
from threading import Thread
from datetime import datetime
from flask import Flask
from telegram import Bot

print("=" * 50)
print("🤖 БОТ: ПРИВЕТ КРИВЕТКА")
print("=" * 50)

# 1. Получаем токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# 2. Flask ДОЛЖЕН БЫТЬ ОПРЕДЕЛЁН ДО создания потоков
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот работает! Он отправляет 'Привет Криветка' каждую минуту."

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    """Запускает Flask в отдельном потоке"""
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# 3. Асинхронные функции для работы с Telegram
async def get_chat_id_async():
    """Асинхронно получает chat_id"""
    try:
        bot = Bot(token=BOT_TOKEN)
        updates = await bot.get_updates()
        
        if updates:
            chat_id = updates[-1].message.chat_id
            print(f"✅ Найден чат ID: {chat_id}")
            return chat_id
        else:
            print("⚠️ Боту ещё никто не писал. Напиши ему в Telegram!")
            return None
    except Exception as e:
        print(f"❌ Ошибка получения chat_id: {e}")
        return None

async def send_message_async(chat_id):
    """Асинхронно отправляет сообщение"""
    try:
        bot = Bot(token=BOT_TOKEN)
        now = datetime.now().strftime("%H:%M:%S")
        message = f"🦐 Привет Криветка! {now}"
        
        await bot.send_message(chat_id=chat_id, text=message)
        print(f"✅ Отправлено: {message}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

# 4. Синхронные обёртки
def get_chat_id():
    return asyncio.run(get_chat_id_async())

def send_message(chat_id):
    return asyncio.run(send_message_async(chat_id))

# 5. Основной цикл бота (ЭТО ГЛАВНЫЙ ПОТОК!)
def bot_main_loop():
    """Основной цикл отправки сообщений"""
    print("⏰ Запуск цикла сообщений...")
    print("📱 Найди бота в Telegram и напиши ему любое сообщение!")
    
    chat_id = None
    attempts = 0
    
    while True:
        if not chat_id:
            print(f"🔄 Попытка {attempts+1}: ищу chat_id...")
            chat_id = get_chat_id()
            attempts += 1
            
            if not chat_id:
                print("⏳ Жду 30 секунд перед следующей попыткой...")
                time.sleep(30)
                continue
            else:
                print("🎉 Chat_id найден! Начинаю отправку...")
                # Отправляем первое сообщение сразу
                send_message(chat_id)
        
        # Отправляем регулярные сообщения
        try:
            send_message(chat_id)
        except Exception as e:
            print(f"❌ Ошибка: {e}. Сбрасываю chat_id...")
            chat_id = None
            continue
        
        # Ждём 60 секунд до следующей отправки
        print(f"⏳ Следующее сообщение через 60 секунд...")
        time.sleep(60)

# 6. Главная функция - ЗАПУСКАЕМ ВСЁ ПРАВИЛЬНО
if __name__ == "__main__":
    # ЗАПУСКАЕМ Flask В ОТДЕЛЬНОМ ПОТОКЕ СРАЗУ
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(3)  # Даём Flask время запуститься
    print("🌐 Flask запущен на порту 10000")
    
    # ЗАПУСКАЕМ ОСНОВНОЙ ЦИКЛ БОТА В ГЛАВНОМ ПОТОКЕ
    # Это важно - главный поток не должен быть занят Flask!
    try:
        bot_main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
