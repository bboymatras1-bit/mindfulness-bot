import os
import time
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
import requests

print("=" * 50)
print("🤖 MINDFULNESS КРИВЕТКА - ВЕБХУК ВЕРСИЯ")
print("=" * 50)

# 1. Настройки
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен: {BOT_TOKEN[:10]}...")

# 2. База данных
DB_FILE = "mindfulness_responses.json"

def save_response(user_id, username, question, answer, timestamp):
    """Сохраняет ответ в JSON файл"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"sessions": [], "responses": []}
        
        today = datetime.now().strftime("%Y-%m-%d")
        session = next((s for s in data["sessions"] if s["date"] == today and s["user_id"] == user_id), None)
        
        if not session:
            session = {
                "user_id": user_id,
                "username": username,
                "date": today,
                "start_time": datetime.now().isoformat()
            }
            data["sessions"].append(session)
        
        data["responses"].append({
            "user_id": user_id,
            "username": username,
            "question": question,
            "answer": answer,
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Ответ сохранён: {user_id} -> {question[:20]}... = {answer}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def get_user_stats(user_id):
    """Статистика по пользователю"""
    if not os.path.exists(DB_FILE):
        return {"total": 0, "today": 0, "conscious": 0}
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        today = datetime.now().strftime("%Y-%m-%d")
        user_responses = [r for r in data.get("responses", []) if r.get("user_id") == user_id]
        today_responses = [r for r in user_responses if r.get("date", "").startswith(today)]
        
        conscious = sum(1 for r in user_responses if "сознателен" in r.get("answer", ""))
        
        return {
            "total": len(user_responses),
            "today": len(today_responses),
            "conscious": conscious,
            "conscious_percent": (conscious / len(user_responses) * 100) if user_responses else 0
        }
    except:
        return {"total": 0, "today": 0, "conscious": 0}

# 3. Вопросы для Mindfulness Криветки
MINDFULNESS_QUESTIONS = [
    {
        "id": "conscious",
        "text": "🧘 *Ты сейчас сознателен?*",
        "options": [
            {"text": "✅ Да, я полностью здесь и сейчас", "callback": "conscious_yes_full"},
            {"text": "🤔 Частично, мысли блуждают", "callback": "conscious_yes_partial"},
            {"text": "😴 Нет, действую на автопилоте", "callback": "conscious_no"}
        ]
    },
    {
        "id": "attention",
        "text": "👁️ *На чём сейчас твоё внимание?*",
        "options": [
            {"text": "🎯 На текущей задаче", "callback": "attention_task"},
            {"text": "🌌 На внутренних мыслях", "callback": "attention_thoughts"},
            {"text": "🌍 На внешней среде", "callback": "attention_external"},
            {"text": "🌀 Рассеяно, ни на чём конкретно", "callback": "attention_scattered"}
        ]
    },
    {
        "id": "energy",
        "text": "⚡ *Какой у тебя уровень энергии?*",
        "options": [
            {"text": "🔋 Высокий, полон сил", "callback": "energy_high"},
            {"text": "🔄 Средний, стабильный", "callback": "energy_medium"},
            {"text": "🪫 Низкий, устал", "callback": "energy_low"},
            {"text": "🌊 Волнообразный, то вверх то вниз", "callback": "energy_wave"}
        ]
    },
    {
        "id": "emotion",
        "text": "💖 *Какая сейчас основная эмоция?*",
        "options": [
            {"text": "😊 Спокойствие/радость", "callback": "emotion_calm"},
            {"text": "😐 Нейтральное состояние", "callback": "emotion_neutral"},
            {"text": "😟 Тревога/беспокойство", "callback": "emotion_anxious"},
            {"text": "😤 Раздражение/фрустрация", "callback": "emotion_irritated"},
            {"text": "🤷 Не осознаю эмоции", "callback": "emotion_unaware"}
        ]
    },
    {
        "id": "purpose",
        "text": "🎯 *Помнишь ли о своей главной цели сегодня?*",
        "options": [
            {"text": "✅ Да, чётко представляю", "callback": "purpose_clear"},
            {"text": "🌀 Смутно помню", "callback": "purpose_vague"},
            {"text": "❌ Полностью забыл", "callback": "purpose_forgotten"},
            {"text": "🤔 У меня нет чёткой цели", "callback": "purpose_none"}
        ]
    }
]

# 4. Flask приложение
app = Flask(__name__)

# Глобальные переменные для состояния
user_sessions = {}
question_schedule = {}

# 5. Функции для Telegram API
def send_welcome_message(chat_id, user_name):
    """Отправляет приветственное сообщение с кнопкой Старт"""
    message = f"""🦐 *Я — Mindfulness Криветка!*

Привет, {user_name}! Я буду помогать тебе оставаться осознанным.

Каждые *2 часа* я буду задавать тебе вопросы о твоём состоянии.

📊 *Твои ответы сохраняются* — ты можешь отслеживать свою осознанность.

Нажми кнопку *СТАРТ*, чтобы получить первый вопрос прямо сейчас!"""
    
    # Создаём клавиатуру с кнопкой Старт
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 НАЧАТЬ ПРАКТИКУ", "callback_data": "start_practice"}]
        ]
    }
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"👋 Приветствие отправлено {user_name}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка отправки приветствия: {e}")
        return False

def send_mindfulness_question(chat_id, question_data, user_name=""):
    """Отправляет вопрос с кнопками"""
    keyboard = {"inline_keyboard": []}
    
    for option in question_data["options"]:
        keyboard["inline_keyboard"].append([
            {"text": option["text"], "callback_data": option["callback"]}
        ])
    
    message = f"""🦐 *Mindfulness Криветка*

*Вопрос:*

{question_data['text']}

Выбери ответ:"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if user_name:
            print(f"🦐 Вопрос отправлен {user_name}: {question_data['text'][:30]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка отправки вопроса: {e}")
        return False

# 6. Обработчики Flask
@app.route('/')
def home():
    stats = {"total_users": 0, "total_responses": 0}
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stats["total_users"] = len({r["user_id"] for r in data.get("responses", [])})
                stats["total_responses"] = len(data.get("responses", []))
        except:
            pass
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🦐 Mindfulness Криветка</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .emoji {{
                font-size: 24px;
            }}
            code {{
                background: #f8f9fa;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }}
            .stats {{
                background: #e8f4f8;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1><span class="emoji">🦐</span> Mindfulness Криветка</h1>
            <p>Бот для практики осознанности, который помогает оставаться в моменте.</p>
            
            <div class="stats">
                <h3>📊 Статистика:</h3>
                <ul>
                    <li>👥 Пользователей: {stats['total_users']}</li>
                    <li>📝 Ответов: {stats['total_responses']}</li>
                    <li>⏰ Частота: вопрос каждые 2 часа</li>
                    <li>✅ Статус: Бот работает!</li>
                </ul>
            </div>
            
            <h3>🎯 Как начать:</h3>
            <ol>
                <li>Найдите бота в Telegram</li>
                <li>Напишите <code>/start</code></li>
                <li>Нажмите кнопку <strong>🚀 НАЧАТЬ ПРАКТИКУ</strong></li>
                <li>Получайте вопросы о вашем состоянии</li>
                <li>Отвечайте нажимая на кнопки</li>
            </ol>
            
            <h3>⏰ Режим работы:</h3>
            <ul>
                <li>Первый вопрос - сразу после нажатия кнопки "Старт"</li>
                <li>Следующие вопросы - каждые 2 часа</li>
                <li>Все ответы сохраняются</li>
                <li>Доступна статистика (<code>/stats</code>)</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основной обработчик вебхуков от Telegram"""
    try:
        update = request.get_json()
        
        # Команда /start
        if 'message' in update and 'text' in update['message']:
            text = update['message']['text']
            chat_id = update['message']['chat']['id']
            user = update['message']['from']
            user_name = user.get('first_name', 'друг')
            
            print(f"📩 Сообщение от {user_name}: {text}")
            
            if text == '/start':
                # Отправляем приветственное сообщение
                send_welcome_message(chat_id, user_name)
                
                # Регистрируем пользователя
                user_sessions[chat_id] = {
                    "user_id": user['id'],
                    "user_name": user_name,
                    "question_index": 0,
                    "start_time": time.time(),
                    "waiting_for_start": True
                }
                
                print(f"🦐 Новый пользователь: {user_name}")
                
            elif text == '/stats':
                stats = get_user_stats(user['id'])
                
                if stats["total"] == 0:
                    message = f"📊 *Статистика для {user_name}*\n\nПока нет ответов. Начни практику!"
                else:
                    message = f"""📊 *Статистика осознанности для {user_name}*

• Всего ответов: {stats['total']}
• Сегодня: {stats['today']} ответов
• Состояний сознания: {stats['conscious']}
• Процент осознанности: {stats['conscious_percent']:.1f}%

Продолжай практиковать осознанность! 🧘"""
                
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                })
                
            elif text == '/help':
                help_text = """🦐 *Mindfulness Криветка - Помощь*

Доступные команды:
/start - начать работу с ботом
/stats - посмотреть свою статистику
/help - эта справка

Нажмите кнопку "НАЧАТЬ ПРАКТИКУ" чтобы получить первый вопрос!"""
                
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": help_text,
                    "parse_mode": "Markdown"
                })
        
        # Обработка нажатий кнопок
        elif 'callback_query' in update:
            callback = update['callback_query']
            user = callback['from']
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            user_name = user.get('first_name', 'друг')
            
            print(f"🖱️ Кнопка от {user_name}: {callback_data}")
            
            # Если нажата кнопка "СТАРТ"
            if callback_data == "start_practice":
                # Начинаем практику
                if chat_id in user_sessions:
                    # Убираем флаг ожидания
                    user_sessions[chat_id]["waiting_for_start"] = False
                
                # Отправляем первый вопрос
                question_index = user_sessions.get(chat_id, {}).get("question_index", 0)
                question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
                
                send_mindfulness_question(chat_id, question, user_name)
                print(f"🚀 Первый вопрос отправлен {user_name}")
                
                # Планируем следующий вопрос через 2 часа
                question_schedule[chat_id] = time.time() + 7200
                
                # Обновляем индекс вопроса
                if chat_id in user_sessions:
                    user_sessions[chat_id]["question_index"] = question_index + 1
                
                # Подтверждаем нажатие кнопки
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": callback['id'],
                    "text": "Начинаем практику!",
                    "show_alert": False
                })
            
            # Обработка ответов на вопросы
            else:
                # Сохраняем ответ
                for question in MINDFULNESS_QUESTIONS:
                    for option in question["options"]:
                        if option["callback"] == callback_data:
                            save_response(
                                user['id'],
                                user.get('username', user_name),
                                question["text"],
                                option["text"],
                                datetime.now().isoformat()
                            )
                            break
                
                # Подтверждаем получение ответа
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": callback['id'],
                    "text": "✅ Ответ записан!",
                    "show_alert": False
                })
                
                # Отправляем подтверждение в чат
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "✅ Твой ответ сохранён! Следующий вопрос через 2 часа.",
                    "parse_mode": "Markdown"
                })
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в вебхуке: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_scheduled_questions():
    """Фоновая задача для отправки запланированных вопросов"""
    while True:
        try:
            current_time = time.time()
            
            for chat_id, next_time in list(question_schedule.items()):
                if current_time >= next_time and chat_id in user_sessions:
                    session = user_sessions[chat_id]
                    
                    # Проверяем, что пользователь уже начал практику
                    if session.get("waiting_for_start", False):
                        continue
                    
                    # Выбираем вопрос
                    question_index = session["question_index"]
                    question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
                    
                    # Отправляем вопрос
                    if send_mindfulness_question(chat_id, question, session["user_name"]):
                        print(f"🦐 Вопрос по расписанию для {session['user_name']}")
                        
                        # Обновляем расписание
                        question_schedule[chat_id] = current_time + 7200
                        
                        # Переходим к следующему вопросу
                        user_sessions[chat_id]["question_index"] = question_index + 1
            
            # Пауза 10 секунд между проверками
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Ошибка в фоновой задаче: {e}")
            time.sleep(30)

def setup_webhook():
    """Устанавливает вебхук"""
    try:
        # Удаляем старый вебхук
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        requests.post(delete_url, timeout=5)
        print("🗑️ Старый вебхук удалён")
        
        # Устанавливаем новый вебхук
        webhook_url = f"https://mindfulness-bot-1.onrender.com/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        
        response = requests.post(set_url, json={"url": webhook_url}, timeout=10)
        print(f"🌐 Вебхук установлен: {response.json()}")
        
    except Exception as e:
        print(f"⚠️ Ошибка настройки вебхука: {e}")

# 7. Запуск приложения
if __name__ == "__main__":
    # Устанавливаем вебхук
    setup_webhook()
    
    # Запускаем фоновую задачу для отправки вопросов
    scheduler_thread = threading.Thread(target=send_scheduled_questions, daemon=True)
    scheduler_thread.start()
    
    # Запускаем Flask
    print("🚀 Запускаю Flask сервер...")
    print(f"🔗 Веб-интерфейс: https://mindfulness-bot-1.onrender.com")
    print(f"🔗 Вебхук: https://mindfulness-bot-1.onrender.com/webhook")
    print("🤖 Бот готов к работе! Напишите /start в Telegram")
    
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
