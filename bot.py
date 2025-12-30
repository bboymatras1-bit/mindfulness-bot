import os
import time
from datetime import datetime

from flask import Flask
from threading import Thread

print("=" * 50)
print("🤖 БОТ: ПРИВЕТ КРИВЕТКА")
print("=" * 50)

# 1. Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ Нет токена!")
    exit(1)
print(f"✅ Токен: {BOT_TOKEN[:10]}...")

# 2. Flask для Render
app = Flask(__name__)
@app.route('/') 
def home(): return "🤖 Бот 'Привет Криветка' работает!"
@app.route('/health') 
def health(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

Thread(target=run_flask, daemon=True).start()
time.sleep(2)
print("🌐 Flask запущен")

# 3. Функции Telegram
def get_chat_id():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        if response.ok and response.json().get('result'):
            return response.json()['result'][-1]['message']['chat']['id']
    except:
        pass
    return None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
        return True
    except:
        return False

# 4. Основной цикл
print("⏰ Запускаю бота...")
print("📱 Напиши боту в Telegram ЛЮБОЕ сообщение!")

chat_id = None
counter = 0

while True:
    counter += 1
    
    if not chat_id:
        print(f"🔄 Попытка {counter}: ищу chat_id...")
        chat_id = get_chat_id()
        
        if not chat_id:
            print("⚠️ Напиши боту в Telegram!")
            time.sleep(30)
            continue
        else:
            print(f"✅ Найден chat_id: {chat_id}")
    
    # Отправляем
    now = datetime.now().strftime("%H:%M:%S")
    message = f"🦐 Привет Криветка! {now}"
    
    if send_message(chat_id, message):
        print(f"✅ Отправлено: {now}")
    else:
        print("❌ Ошибка. Пробую заново...")
        chat_id = None
    
    time.sleep(60)

