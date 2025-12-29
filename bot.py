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

# 2. Flask для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот работает! Он отправляет 'Привет Криветка' каждую минуту."

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# 3. Асинхронная функция для получения chat_id
async def get_chat_id_async():
    """Асинхронно получает chat_id из обновлений"""
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

# 4. Синхронные обёртки для асинхронных функций
def get_chat_id():
    """Синхронная обёртка для получения chat_id"""
    return asyncio.run(get_chat_id_async())

def send_message(chat_id):
    """Синхронная обёртка для отправки сообщения"""
    return asyncio.run(send_message_async(chat_id))

# 5. Главный цикл
def main_loop():
    print("⏰ Запуск цикла сообщений...")
    
    chat_id = None
    bot_started = False
    
    while True:
        if not chat_id:
            print("🔄 Ищу chat_id...")
            chat_id = get_chat_id()
            
            if chat_id and not bot_started:
                print("🎉 Бот готов к отправке сообщений!")
                bot_started = True
                
        else:
            # Отправляем сообщение
            success = send_message(chat_id)
            
            if not success:
                print("🔄 Сбрасываю chat_id из-за ошибки...")
                chat_id = None
                time.sleep(5)  # Пауза перед повторной попыткой
                continue
        
        time.sleep(60)  # Ждём 60 секунд

# 6. Запуск всего
if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    print("🌐 Flask запущен на порту 10000")
    print("📱 Теперь найди своего бота в Telegram и напиши ему любое сообщение!")
    
    # Запускаем основной цикл
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
