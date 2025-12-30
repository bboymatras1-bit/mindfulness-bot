import os
import time
import json
from datetime import datetime
from flask import Flask
import requests

print("=" * 50)
print("🤖 MINDFULNESS BOT - ПРОВЕРКА СОЗНАТЕЛЬНОСТИ")
print("=" * 50)

# 1. Настройки
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен: {BOT_TOKEN[:10]}...")

# 2. База данных для хранения ответов
DB_FILE = "responses.json"

def save_response(user_id, username, answer, timestamp):
    """Сохраняет ответ в JSON файл"""
    try:
        # Загружаем существующие данные
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"responses": []}
        
        # Добавляем новый ответ
        data["responses"].append({
            "user_id": user_id,
            "username": username,
            "answer": answer,
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Сохраняем
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Ответ сохранён: {user_id} -> {answer}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def get_stats():
    """Возвращает статистику ответов"""
    if not os.path.exists(DB_FILE):
        return {"total": 0, "yes": 0, "no": 0}
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        responses = data.get("responses", [])
        yes_count = sum(1 for r in responses if r.get("answer") == "Да, я сознателен")
        no_count = sum(1 for r in responses if r.get("answer") == "Нет, я сплю")
        
        return {
            "total": len(responses),
            "yes": yes_count,
            "no": no_count,
            "yes_percent": (yes_count / len(responses) * 100) if responses else 0
        }
    except:
        return {"total": 0, "yes": 0, "no": 0}

# 3. Flask для Render
app = Flask(__name__)

@app.route('/')
def home():
    stats = get_stats()
    return f"""
    <h1>🧘 Mindfulness Bot</h1>
    <p>Бот задаёт вопрос "Ты сейчас сознателен?" каждые 2 минуты</p>
    
    <h3>📊 Статистика:</h3>
    <ul>
        <li>Всего ответов: {stats['total']}</li>
        <li>✅ Сознательных: {stats['yes']}</li>
        <li>😴 На автопилоте: {stats['no']}</li>
        <li>📈 Процент сознательности: {stats.get('yes_percent', 0):.1f}%</li>
    </ul>
    
    <p><a href="/health">Health Check</a> | <a href="/send_now">Отправить вопрос сейчас</a></p>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/send_now')
def send_now():
    """Ручная отправка вопроса"""
    return """
    <h2>📨 Отправить вопрос вручную</h2>
    <p>Эта функция работает через Telegram API.</p>
    <p>Бот автоматически отправляет вопрос каждые 2 минуты.</p>
    <p><a href="/">Назад</a></p>
    """

# 4. Функции для работы с Telegram API
def send_question(chat_id):
    """Отправляет вопрос с кнопками"""
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Да, я сейчас сознателен", "callback_data": "conscious_yes"},
            {"text": "😴 Нет, я сейчас сплю", "callback_data": "conscious_no"}
        ]]
    }
    
    message = "🧘 *Вопрос для проверки:*\\n\\n*Ты сейчас сознателен?*"
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"📨 Вопрос отправлен в чат {chat_id}")
            return True
        else:
            print(f"❌ Ошибка отправки: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def process_callback(callback_data, user_id, username, message_id):
    """Обрабатывает нажатие кнопки"""
    if callback_data == "conscious_yes":
        answer = "Да, я сознателен"
    elif callback_data == "conscious_no":
        answer = "Нет, я сплю"
    else:
        return False
    
    # Сохраняем ответ
    save_response(user_id, username, answer, datetime.now().isoformat())
    
    # Отправляем подтверждение
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": message_id,
        "text": f"✅ Ответ записан: {answer}",
        "show_alert": False
    }
    
    requests.post(url, json=payload, timeout=5)
    return True

# 5. Основной цикл бота
def bot_main_loop():
    """Основной цикл отправки вопросов"""
    print("⏰ Запускаю Mindfulness Bot...")
    print("📱 Напиши боту /start в Telegram для начала")
    
    last_chats = {}  # {chat_id: last_question_time}
    
    while True:
        try:
            # 1. Проверяем обновления (команды и callback'и)
            updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            response = requests.get(updates_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result'):
                    for update in data['result']:
                        # Обработка команды /start
                        if 'message' in update and 'text' in update['message']:
                            if update['message']['text'] == '/start':
                                chat_id = update['message']['chat']['id']
                                user = update['message']['from']
                                
                                # Приветственное сообщение
                                welcome_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                                welcome_text = f"""🧘 *Привет, {user.get('first_name', 'друг')}!*

Я — Mindfulness Bot. Каждые 2 минуты я буду спрашивать:
*"Ты сейчас сознателен?"*

Просто нажимай на кнопки под сообщением.

📊 Твои ответы сохраняются в статистику.

*Первая проверка через 2 минуты...*"""
                                
                                requests.post(welcome_url, json={
                                    "chat_id": chat_id,
                                    "text": welcome_text,
                                    "parse_mode": "Markdown"
                                })
                                
                                print(f"👋 Новый пользователь: {user.get('first_name')} (ID: {chat_id})")
                                last_chats[chat_id] = 0  # Сразу можно отправить вопрос
                        
                        # Обработка callback от кнопок
                        elif 'callback_query' in update:
                            callback = update['callback_query']
                            user = callback['from']
                            
                            process_callback(
                                callback['data'],
                                user['id'],
                                user.get('username', user.get('first_name', 'unknown')),
                                callback['id']
                            )
            
            # 2. Отправляем вопросы каждые 2 минуты
            current_time = time.time()
            
            for chat_id, last_time in list(last_chats.items()):
                if current_time - last_time >= 120:  # 2 минуты
                    if send_question(chat_id):
                        last_chats[chat_id] = current_time
                        print(f"⏱️ Вопрос отправлен в {datetime.now().strftime('%H:%M:%S')}")
            
            # 3. Показываем статус
            stats = get_stats()
            if stats['total'] > 0:
                print(f"📊 Статистика: {stats['yes']}✅ / {stats['no']}😴 (Всего: {stats['total']})")
            
            # Ждём 10 секунд перед следующей проверкой
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Ошибка в основном цикле: {e}")
            time.sleep(30)

# 6. Запуск всего
if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    from threading import Thread
    bot_thread = Thread(target=bot_main_loop, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask (блокирующий вызов)
    print("🌐 Запускаю Flask сервер...")
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
