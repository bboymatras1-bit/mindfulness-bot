import os
import time
import threading
from datetime import datetime
from flask import Flask
from telegram import Bot

print("=" * 50)
print("🤖 БОТ: ПРИВЕТ КРИВЕТКА (сам себе)")
print("=" * 50)

# 1. Получаем токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    print("   Добавь в Render: Environment -> BOT_TOKEN")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# 2. Отправляем сообщение боту самому себе
def send_to_bot():
    """Бот отправляет сообщение самому себе"""
    try:
        bot = Bot(token=BOT_TOKEN)
        
        # Бот получает свои обновления
        updates = bot.get_updates()
        
        if updates:
            # Берем первый чат, куда писал боту
            chat_id = updates[-1].message.chat_id
            print(f"✅ Найден чат ID: {chat_id}")
        else:
            # Если боту ещё никто не писал, он не может отправить сам себе
            print("⚠️ Боту ещё никто не писал. Напиши ему что-нибудь в Telegram!")
            return None
        
        # Отправляем сообщение
        now = datetime.now().strftime("%H:%M:%S")
        message = f"🦐 Привет Криветка! {now}"
        
        bot.send_message(chat_id=chat_id, text=message)
        print(f"✅ Отправлено: {message}")
        return chat_id
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

# 3. Flask для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот работает! Он отправляет 'Привет Криветка' сам себе."

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# 4. Главный цикл
if __name__ == "__main__":
    # Запускаем Flask
    Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    print("🌐 Flask запущен на порту 10000")
    
    print("⏰ Запуск цикла сообщений...")
    
    # Пробуем получить chat_id при старте
    chat_id = None
    
    # Основной цикл
    while True:
        if not chat_id:
            chat_id = send_to_bot()  # Пытаемся получить chat_id
        else:
            # Если chat_id есть - просто отправляем
            try:
                bot = Bot(token=BOT_TOKEN)
                now = datetime.now().strftime("%H:%M:%S")
                message = f"🦐 Привет Криветка! {now}"
                bot.send_message(chat_id=chat_id, text=message)
                print(f"✅ Отправлено: {message}")
            except Exception as e:
                print(f"❌ Ошибка отправки: {e}")
                chat_id = None  # Сбрасываем chat_id при ошибке
        
        time.sleep(60)  # Ждём 60 секунд
