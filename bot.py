import os
import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import requests
import re

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

def save_response(user_id, username, question, answer, timestamp, question_type="button"):
    """Сохраняет ответ в JSON файл"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"sessions": [], "responses": []}
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Находим или создаём сессию за сегодня
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
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question_type": question_type
        })
        
        # Ограничиваем количество ответов (например, последние 1000)
        if len(data["responses"]) > 1000:
            data["responses"] = data["responses"][-1000:]
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Ответ сохранён: {user_id} -> {question[:20]}... = {answer}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def get_user_stats(user_id, period_days=1):
    """Статистика по пользователю за указанный период"""
    if not os.path.exists(DB_FILE):
        return {"total": 0, "today": 0, "conscious": 0, "goals_minutes": 0, "daily_summary": []}
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Фильтруем ответы за последние N дней
        cutoff_date = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
        user_responses = [
            r for r in data.get("responses", []) 
            if r.get("user_id") == user_id and r.get("date", "") >= cutoff_date
        ]
        
        # Ответы за сегодня
        today = datetime.now().strftime("%Y-%m-%d")
        today_responses = [r for r in user_responses if r.get("date", "").startswith(today)]
        
        # Подсчёт состояний сознания
        conscious = sum(1 for r in user_responses if "сознателен" in r.get("answer", ""))
        
        # Подсчёт времени на цели (из текстовых ответов)
        goals_minutes = 0
        for r in user_responses:
            if "Сколько времени я уделил своей цели?" in r.get("question", ""):
                answer = r.get("answer", "")
                # Ищем число в ответе
                match = re.search(r'(\d+)', answer)
                if match:
                    goals_minutes += int(match.group(1))
        
        # Создаём ежедневную сводку
        daily_summary = []
        dates = sorted(set(r.get("date", "")[:10] for r in user_responses))
        
        for date in dates[-7:]:  # Последние 7 дней
            date_responses = [r for r in user_responses if r.get("date", "").startswith(date)]
            conscious_count = sum(1 for r in date_responses if "сознателен" in r.get("answer", ""))
            
            # Время на цели за день
            daily_goals = 0
            for r in date_responses:
                if "Сколько времени я уделил своей цели?" in r.get("question", ""):
                    answer = r.get("answer", "")
                    match = re.search(r'(\d+)', answer)
                    if match:
                        daily_goals += int(match.group(1))
            
            daily_summary.append({
                "date": date,
                "responses": len(date_responses),
                "conscious": conscious_count,
                "goals_minutes": daily_goals
            })
        
        return {
            "total": len(user_responses),
            "today": len(today_responses),
            "conscious": conscious,
            "conscious_percent": (conscious / len(user_responses) * 100) if user_responses else 0,
            "goals_minutes": goals_minutes,
            "daily_summary": daily_summary,
            "period_days": period_days
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {"total": 0, "today": 0, "conscious": 0, "goals_minutes": 0, "daily_summary": []}

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
        "id": "time_for_goal",
        "text": "⏱️ *Сколько времени я уделил своей цели?*\n_(Ответ в минутах, например: 30)_",
        "input_required": True  # Этот вопрос требует текстового ответа
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
awaiting_time_response = {}  # {user_id: True} - пользователь ждёт ответ на вопрос о времени

# 5. Функции для Telegram API
def send_welcome_message(chat_id, user_name):
    """Отправляет приветственное сообщение с кнопкой Старт"""
    message = f"""🦐 *Я — Mindfulness Криветка!*

Привет, {user_name}! Я буду помогать тебе оставаться осознанным.

Каждые *2 часа* я буду задавать тебе вопросы о твоём состоянии.

📊 *Все твои ответы сохраняются* — ты можешь отслеживать свою осознанность с помощью команды /stats

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
    """Отправляет вопрос с кнопками или текстовый вопрос"""
    
    # Проверяем, требует ли вопрос текстового ответа
    if question_data.get("input_required"):
        # Вопрос о времени - просто отправляем текст
        message = f"""🦐 *Mindfulness Криветка*

*Вопрос:*

{question_data['text']}

_Пожалуйста, введи число минут (например: 30)_"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if user_name:
                print(f"⏱️ Вопрос о времени отправлен {user_name}")
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки вопроса о времени: {e}")
            return False
    else:
        # Обычный вопрос с кнопками
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

def format_stats_message(stats, user_name):
    """Форматирует сообщение со статистикой"""
    if stats["total"] == 0:
        return f"""📊 *Статистика для {user_name}*

Пока нет ответов. Начни практику! 🚀"""
    
    # Форматируем ежедневную сводку
    summary_text = ""
    for day in stats["daily_summary"]:
        date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m")
        summary_text += f"📅 *{date_str}:* {day['responses']} ответов, {day['conscious']} осознанных, {day['goals_minutes']} мин на цели\n"
    
    total_hours = stats["goals_minutes"] // 60
    total_minutes = stats["goals_minutes"] % 60
    
    return f"""📊 *Статистика осознанности для {user_name}*

*За последние {stats['period_days']} дней:*
• Всего ответов: {stats['total']}
• Сегодня: {stats['today']} ответов
• Осознанных состояний: {stats['conscious']}
• Процент осознанности: {stats['conscious_percent']:.1f}%
• Время на цели: {stats['goals_minutes']} мин ({total_hours} ч {total_minutes} мин)

*Ежедневная сводка (последние 7 дней):*
{summary_text}

Продолжай практиковать осознанность! 🧘"""

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
                <li>На вопрос о времени вводите число минут</li>
            </ol>
            
            <h3>📈 Команды:</h3>
            <ul>
                <li><code>/start</code> - начать</li>
                <li><code>/stats</code> - статистика</li>
                <li><code>/help</code> - помощь</li>
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
        
        # Обработка текстовых сообщений
        if 'message' in update and 'text' in update['message']:
            text = update['message']['text']
            chat_id = update['message']['chat']['id']
            user = update['message']['from']
            user_id = user['id']
            user_name = user.get('first_name', 'друг')
            
            print(f"📩 Сообщение от {user_name}: {text}")
            
            # Проверяем, не ждёт ли пользователь ответ на вопрос о времени
            if user_id in awaiting_time_response and awaiting_time_response[user_id]:
                # Пользователь отвечает на вопрос о времени
                await_time_response(chat_id, user_id, user_name, text)
                return jsonify({"status": "ok"}), 200
            
            # Обработка команд
            if text == '/start':
                handle_start_command(chat_id, user)
                
            elif text == '/stats':
                handle_stats_command(chat_id, user_id, user_name)
                
            elif text == '/help':
                send_help_message(chat_id)
                
            elif text.startswith('/stats'):
                # Может быть с параметром /stats 7 (за 7 дней)
                parts = text.split()
                if len(parts) > 1 and parts[1].isdigit():
                    period = int(parts[1])
                    handle_stats_command(chat_id, user_id, user_name, period)
                else:
                    handle_stats_command(chat_id, user_id, user_name)
            
            else:
                # Неизвестная команда или текст
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "Используйте команды: /start, /stats, /help",
                    "parse_mode": "Markdown"
                })
        
        # Обработка нажатий кнопок
        elif 'callback_query' in update:
            callback = update['callback_query']
            user = callback['from']
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            user_name = user.get('first_name', 'друг')
            user_id = user['id']
            
            print(f"🖱️ Кнопка от {user_name}: {callback_data}")
            
            # Если нажата кнопка "СТАРТ"
            if callback_data == "start_practice":
                start_practice_for_user(chat_id, user_id, user_name)
                
                # Подтверждаем нажатие кнопки
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": callback['id'],
                    "text": "Начинаем практику!",
                    "show_alert": False
                })
            
            # Обработка ответов на вопросы с кнопками
            else:
                handle_button_response(callback, user_id, user_name, chat_id)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка в вебхуке: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def handle_start_command(chat_id, user):
    """Обрабатывает команду /start"""
    user_name = user.get('first_name', 'Друг')
    user_id = user['id']
    
    # Отправляем приветственное сообщение
    send_welcome_message(chat_id, user_name)
    
    # Регистрируем пользователя
    user_sessions[chat_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "question_index": 0,
        "start_time": time.time(),
        "waiting_for_start": True
    }
    
    print(f"🦐 Новый пользователь: {user_name}")

def handle_stats_command(chat_id, user_id, user_name, period_days=7):
    """Обрабатывает команду /stats"""
    stats = get_user_stats(user_id, period_days)
    message = format_stats_message(stats, user_name)
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    })

def send_help_message(chat_id):
    """Отправляет справку"""
    help_text = """🦐 *Mindfulness Криветка - Помощь*

*Доступные команды:*
/start - начать работу с ботом
/stats - статистика за последние 7 дней
/stats N - статистика за N дней (например: /stats 30)
/help - эта справка

*Как работает бот:*
1. Нажмите кнопку "НАЧАТЬ ПРАКТИКУ"
2. Получайте вопросы каждые 2 часа
3. На вопросы отвечайте нажатием кнопок
4. На вопрос о времени введите число минут
5. Все ответы сохраняются

*Вопрос о времени:*
Когда бот спросит "Сколько времени я уделил своей цели?" - просто введите число минут (например: 45)"""

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": chat_id,
        "text": help_text,
        "parse_mode": "Markdown"
    })

def start_practice_for_user(chat_id, user_id, user_name):
    """Начинает практику для пользователя"""
    if chat_id not in user_sessions:
        # Регистрируем пользователя
        user_sessions[chat_id] = {
            "user_id": user_id,
            "user_name": user_name,
            "question_index": 0,
            "start_time": time.time()
        }
    
    # Убираем флаг ожидания старта
    if "waiting_for_start" in user_sessions[chat_id]:
        user_sessions[chat_id]["waiting_for_start"] = False
    
    # Отправляем первый вопрос
    question_index = user_sessions[chat_id]["question_index"]
    question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
    
    if send_mindfulness_question(chat_id, question, user_name):
        print(f"🚀 Первый вопрос отправлен {user_name}")
        
        # Если это вопрос о времени, отмечаем что ждём ответ
        if question.get("input_required"):
            awaiting_time_response[user_id] = True
        
        # Планируем следующий вопрос через 2 часа
        question_schedule[chat_id] = time.time() + 7200
        
        # Переходим к следующему вопросу
        user_sessions[chat_id]["question_index"] = question_index + 1
    else:
        print(f"❌ Не удалось отправить вопрос {user_name}")

def handle_button_response(callback, user_id, user_name, chat_id):
    """Обрабатывает ответ на вопрос с кнопками"""
    callback_data = callback['data']
    
    # Сохраняем ответ
    for question in MINDFULNESS_QUESTIONS:
        if "options" in question:
            for option in question["options"]:
                if option["callback"] == callback_data:
                    save_response(
                        user_id,
                        callback['from'].get('username', user_name),
                        question["text"],
                        option["text"],
                        datetime.now().isoformat(),
                        "button"
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

def await_time_response(chat_id, user_id, user_name, text):
    """Обрабатывает ответ на вопрос о времени"""
    # Проверяем, является ли ответ числом
    if text.isdigit():
        minutes = int(text)
        
        if minutes >= 0 and minutes <= 1440:  # Максимум 24 часа в минутах
            # Сохраняем ответ
            question_text = "Сколько времени я уделил своей цели?"
            save_response(
                user_id,
                user_name,
                question_text,
                f"{minutes} минут",
                datetime.now().isoformat(),
                "text"
            )
            
            # Сбрасываем флаг ожидания
            awaiting_time_response[user_id] = False
            
            # Отправляем подтверждение
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ Записал: {minutes} минут уделено цели! Следующий вопрос через 2 часа.",
                "parse_mode": "Markdown"
            })
        else:
            # Число вне допустимого диапазона
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": chat_id,
                "text": "❌ Пожалуйста, введите число от 0 до 1440 (максимум 24 часа).\nСколько минут вы уделили цели?",
                "parse_mode": "Markdown"
            })
    else:
        # Не число
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": "❌ Пожалуйста, введите только число (например: 30).\nСколько минут вы уделили цели?",
            "parse_mode": "Markdown"
        })

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
                        print(f"🦐 Вопрос по расписанию для {session['user_name']}: {question['id']}")
                        
                        # Если это вопрос о времени, отмечаем что ждём ответ
                        if question.get("input_required"):
                            awaiting_time_response[session["user_id"]] = True
                        
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
    print("📊 Все ответы сохраняются, статистика доступна по /stats")
    
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
