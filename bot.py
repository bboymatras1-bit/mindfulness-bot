import os
import time
import json
import random
from datetime import datetime, timedelta
from flask import Flask
import requests

print("=" * 50)
print("🤖 MINDFULNESS КРИВЕТКА - РАСШИРЕННЫЙ")
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
        
        # Находим или создаём сессию за сегодня
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
        
        # Добавляем ответ
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

# 4. Flask для Render
app = Flask(__name__)

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
    <h1>🦐 Mindfulness Криветка</h1>
    <p>Бот для осознанности, который задаёт вопросы каждые 2 часа</p>
    
    <h3>📊 Общая статистика:</h3>
    <ul>
        <li>👥 Пользователей: {stats['total_users']}</li>
        <li>📝 Всего ответов: {stats['total_responses']}</li>
        <li>⏰ Частота: вопрос каждые 2 часа</li>
        <li>❓ Вопросов в наборе: {len(MINDFULNESS_QUESTIONS)}</li>
    </ul>
    
    <h3>🎯 Как использовать:</h3>
    <ol>
        <li>Напиши боту <code>/start</code> в Telegram</li>
        <li>Получай вопросы каждые 2 часа</li>
        <li>Отвечай нажимая кнопки</li>
        <li>Следи за своей осознанностью!</li>
    </ol>
    
    <p><a href="/health">Health Check</a> | <a href="/questions">Список вопросов</a></p>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/questions')
def questions():
    html = "<h2>📋 Все вопросы Mindfulness Криветки:</h2>"
    
    for i, q in enumerate(MINDFULNESS_QUESTIONS, 1):
        html += f"""
        <div style="border: 1px solid #ccc; padding: 15px; margin: 10px; border-radius: 10px;">
            <h3>❓ Вопрос {i}: {q['text'].replace('*', '')}</h3>
            <ul>
        """
        for opt in q['options']:
            html += f"<li>{opt['text']}</li>"
        html += "</ul></div>"
    
    html += '<p><a href="/">На главную</a></p>'
    return html

# 5. Функции для работы с Telegram API
def send_intro_message(chat_id, user_name):
    """Отправляет вступительное сообщение"""
    message = f"""🦐 *Я — Mindfulness Криветка!*

Привет, {user_name}! Я буду помогать тебе оставаться осознанным.

Каждые *2 часа* я буду задавать тебе вопросы о твоём состоянии. 
Не нужно ничего печатать — просто нажимай на кнопки под сообщением.

📊 *Твои ответы сохраняются* — ты можешь отслеживать свою осознанность.

⏰ *Первый вопрос через 2 минуты...*

Напиши /help чтобы увидеть команды
Напиши /stats чтобы увидеть свою статистику"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"👋 Вступление отправлено {user_name}")
        return True
    except:
        return False

def send_mindfulness_question(chat_id, question_data):
    """Отправляет вопрос с кнопками"""
    # Создаём клавиатуру с кнопками
    keyboard = {"inline_keyboard": []}
    
    for option in question_data["options"]:
        keyboard["inline_keyboard"].append([
            {"text": option["text"], "callback_data": option["callback"]}
        ])
    
    # Формируем полное сообщение
    message = f"""🦐 *Mindfulness Криветка*

*Вопрос #{question_data['id']}:*

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
        return response.status_code == 200
    except:
        return False

def send_stats_message(chat_id, user_id, user_name):
    """Отправляет статистику пользователю"""
    stats = get_user_stats(user_id)
    
    if stats["total"] == 0:
        message = f"📊 *Статистика для {user_name}*\n\nПока нет ответов. Дождись первого вопроса!"
    else:
        message = f"""📊 *Статистика осознанности для {user_name}*

• Всего ответов: {stats['total']}
• Сегодня: {stats['today']} ответов
• Состояний сознания: {stats['conscious']}
• Процент осознанности: {stats['conscious_percent']:.1f}%

Продолжай практиковать осознанность! 🧘"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    requests.post(url, json=payload, timeout=10)

# 6. Основной цикл бота
def bot_main_loop():
    """Основной цикл отправки вопросов"""
    print("⏰ Запускаю Mindfulness Криветку...")
    print("📱 Напиши боту /start в Telegram")
    
    # Храним состояние пользователей: {chat_id: {"last_question": timestamp, "question_index": 0, "user_name": "..."}}
    user_sessions = {}
    question_schedule = {}  # Расписание вопросов по пользователям
    
    while True:
        try:
            # 1. Проверяем обновления от Telegram
            updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            response = requests.get(updates_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result'):
                    for update in data['result']:
                        update_id = update.get('update_id', 0)
                        
                        # Команда /start
                        if 'message' in update and 'text' in update['message']:
                            text = update['message']['text']
                            chat_id = update['message']['chat']['id']
                            user = update['message']['from']
                            
                            if text == '/start':
                                # Отправляем вступление
                                send_intro_message(chat_id, user.get('first_name', 'друг'))
                                
                                # Инициализируем сессию
                                user_sessions[chat_id] = {
                                    "user_id": user['id'],
                                    "user_name": user.get('first_name', 'Друг'),
                                    "last_question": time.time() - 7200 + 120,  # Можно задать вопрос через 2 минуты
                                    "question_index": 0,
                                    "start_time": time.time()
                                }
                                question_schedule[chat_id] = time.time() + 120  # Первый вопрос через 2 минуты
                                
                                print(f"🦐 Новый пользователь: {user.get('first_name')} (ID: {chat_id})")
                            
                            elif text == '/stats':
                                send_stats_message(chat_id, user['id'], user.get('first_name', 'Друг'))
                            
                            elif text == '/help':
                                help_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                                help_text = """🦐 *Mindfulness Криветка - Помощь*

Доступные команды:
/start - начать работу с ботом
/stats - посмотреть свою статистику
/help - эта справка

Бот задаёт вопросы каждые 2 часа.
Просто нажимай на кнопки под сообщениями!"""
                                
                                requests.post(help_url, json={
                                    "chat_id": chat_id,
                                    "text": help_text,
                                    "parse_mode": "Markdown"
                                })
                        
                        # Обработка нажатий кнопок
                        elif 'callback_query' in update:
                            callback = update['callback_query']
                            user = callback['from']
                            chat_id = callback['message']['chat']['id']
                            
                            # Определяем, на какой вопрос ответили
                            callback_data = callback['data']
                            question_type = "_".join(callback_data.split("_")[:-1])
                            
                            # Сохраняем ответ
                            for question in MINDFULNESS_QUESTIONS:
                                for option in question["options"]:
                                    if option["callback"] == callback_data:
                                        save_response(
                                            user['id'],
                                            user.get('username', user.get('first_name', 'unknown')),
                                            question["text"],
                                            option["text"],
                                            datetime.now().isoformat()
                                        )
                                        break
                            
                            # Подтверждаем получение ответа
                            answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                            requests.post(answer_url, json={
                                "callback_query_id": callback['id'],
                                "text": "✅ Ответ записан!",
                                "show_alert": False
                            })
            
            # 2. Отправляем вопросы по расписанию (каждые 2 часа)
            current_time = time.time()
            
            for chat_id, next_question_time in list(question_schedule.items()):
                if current_time >= next_question_time and chat_id in user_sessions:
                    session = user_sessions[chat_id]
                    
                    # Выбираем вопрос (по кругу)
                    question_index = session["question_index"]
                    question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
                    
                    # Отправляем вопрос
                    if send_mindfulness_question(chat_id, question):
                        print(f"🦐 Вопрос отправлен {session['user_name']}: {question['text'][:30]}...")
                        
                        # Обновляем расписание: следующий вопрос через 2 часа
                        question_schedule[chat_id] = current_time + 7200  # 2 часа в секундах
                        
                        # Переходим к следующему вопросу
                        user_sessions[chat_id]["question_index"] = question_index + 1
                        user_sessions[chat_id]["last_question"] = current_time
                    
                    else:
                        print(f"❌ Не удалось отправить вопрос {session['user_name']}")
            
            # 3. Логируем статус
            active_users = len(user_sessions)
            if active_users > 0:
                print(f"👥 Активных пользователей: {active_users}")
                print(f"⏰ Следующие вопросы: {len([t for t in question_schedule.values() if t - time.time() < 3600])} в течение часа")
            
            # Пауза 10 секунд
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Ошибка в основном цикле: {e}")
            time.sleep(30)

# 7. Запуск
if __name__ == "__main__":
    # Запускаем бота в фоне
    from threading import Thread
    bot_thread = Thread(target=bot_main_loop, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask
    print("🌐 Запускаю Flask сервер...")
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
