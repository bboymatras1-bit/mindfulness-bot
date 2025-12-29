import os
import time
from multiprocessing import Process
from datetime import datetime
from flask import Flask
import requests  # Для HTTP запросов к Telegram API

print("🤖 ПРОСТОЙ РАБОЧИЙ БОТ")

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ Нет токена!")
    exit(1)

print(f"✅ Токен: {BOT_TOKEN[:10]}...")

# 1. Flask в отдельном процессе
def flask_server():
    app = Flask(__name__)
    @app.route('/') 
    def home(): return "Бот работает"
    @app.route('/health') 
    def health(): return "OK", 200
    print("[FLASK] Сервер запущен")
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# Запускаем Flask
p = Process(target=flask_server, daemon=True)
p.start()
time.sleep(3)
print("🌐 Flask работает")

# 2. Простой цикл бота
print("⏰ Начинаю работу...")

while True:
    try:
        # Пробуем получить обновления
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('result'):
                # Берём последнее сообщение
                last_update = data['result'][-1]
                chat_id = last_update['message']['chat']['id']
                
                # Отправляем сообщение
                now = datetime.now().strftime("%H:%M:%S")
                message = f"🦐 Привет Криветка! {now}"
                
                send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                requests.post(send_url, json={
                    'chat_id': chat_id,
                    'text': message
                })
                
                print(f"✅ Отправлено: {message}")
            else:
                print("⚠️ Напиши боту в Telegram!")
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Ждём 60 секунд
    time.sleep(60)
