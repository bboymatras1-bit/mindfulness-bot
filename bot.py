import os
import time
from flask import Flask
import requests

print("=" * 50)
print("🤖 ПРОСТОЙ РАБОЧИЙ БОТ НА REQUESTS")
print("=" * 50)

# 1. Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен: {BOT_TOKEN[:10]}...")

# 2. Flask для Render
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <h1>🤖 Mindfulness Bot</h1>
    <p>Бот работает на Render!</p>
    <p><a href='/health'>Health Check</a></p>
    <p><a href='/send-test'>Отправить тестовое сообщение</a></p>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/send-test')
def send_test():
    """Ручная отправка тестового сообщения"""
    try:
        # Пробуем найти chat_id
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('result') and len(data['result']) > 0:
                chat_id = data['result'][-1]['message']['chat']['id']
                
                # Отправляем сообщение
                send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                message = f"✅ Тест! Бот работает. Время: {time.strftime('%H:%M:%S')}"
                
                requests.post(send_url, json={
                    'chat_id': chat_id,
                    'text': message
                })
                
                return f"✅ Сообщение отправлено в чат {chat_id}"
            else:
                return "⚠️ Боту ещё не писали. Напиши ему в Telegram!"
        else:
            return f"❌ Ошибка API: {response.status_code}"
            
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

# 3. Функция для отправки сообщений по расписанию
def send_scheduled_message():
    """Отправляет сообщение каждую минуту"""
    print("⏰ Начинаю отправку сообщений...")
    
    while True:
        try:
            # Получаем обновления
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') and len(data['result']) > 0:
                    chat_id = data['result'][-1]['message']['chat']['id']
                    
                    # Отправляем сообщение
                    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    current_time = time.strftime('%H:%M:%S')
                    message = f"🦐 Привет Криветка! {current_time}"
                    
                    requests.post(send_url, json={
                        'chat_id': chat_id,
                        'text': message
                    })
                    
                    print(f"✅ Отправлено в {current_time}")
                else:
                    print("⚠️ Ожидание первого сообщения...")
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        # Ждём 60 секунд
        time.sleep(60)

# 4. Запуск всего
if __name__ == "__main__":
    # Запускаем Flask
    from threading import Thread
    
    # Запускаем отправку сообщений в фоне
    bot_thread = Thread(target=send_scheduled_message, daemon=True)
    bot_thread.start()
    
    print("🌐 Запускаю Flask сервер...")
    print("📱 Напиши боту в Telegram ЛЮБОЕ сообщение!")
    print("⏰ Бот будет отправлять 'Привет Криветка' каждую минуту")
    
    # Запускаем Flask (блокирующий вызов)
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
