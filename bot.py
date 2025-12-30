import os
import time
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import requests
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🤖 MINDFULNESS КРИВЕТКА - УСТОЙЧИВАЯ ВЕРСИЯ")
print("=" * 60)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

logger.info(f"✅ Токен: {BOT_TOKEN[:10]}...")

DB_FILE = "mindfulness_responses.json"

def save_response(user_id, username, question, answer, timestamp, question_type="button"):
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
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question_type": question_type
        })
        
        if len(data["responses"]) > 1000:
            data["responses"] = data["responses"][-1000:]
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Ответ: {user_id} -> {answer}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
        return False

def get_today_responses(user_id):
    if not os.path.exists(DB_FILE):
        return []
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_responses = [
            r for r in data.get("responses", []) 
            if r.get("user_id") == user_id and r.get("date", "").startswith(today)
        ]
        
        today_responses.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return today_responses
    except Exception as e:
        logger.error(f"❌ Ошибка получения ответов за сегодня: {e}")
        return []

def get_user_stats(user_id, period_days=7):
    if not os.path.exists(DB_FILE):
        return {"total": 0, "today": 0, "goals_minutes": 0, "daily_summary": []}
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cutoff_date = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
        user_responses = [
            r for r in data.get("responses", []) 
            if r.get("user_id") == user_id and r.get("date", "") >= cutoff_date
        ]
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_responses = [r for r in user_responses if r.get("date", "").startswith(today)]
        
        goals_minutes = 0
        for r in user_responses:
            if "Сколько времени я уделил своей цели?" in r.get("question", ""):
                answer = r.get("answer", "")
                match = re.search(r'(\d+)', answer)
                if match:
                    goals_minutes += int(match.group(1))
        
        daily_summary = []
        dates = sorted(set(r.get("date", "")[:10] for r in user_responses))
        
        for date in dates[-7:]:
            date_responses = [r for r in user_responses if r.get("date", "").startswith(date)]
            
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
                "goals_minutes": daily_goals
            })
        
        return {
            "total": len(user_responses),
            "today": len(today_responses),
            "goals_minutes": goals_minutes,
            "daily_summary": daily_summary,
            "period_days": period_days
        }
    except Exception as e:
        logger.error(f"❌ Ошибка статистики: {e}")
        return {"total": 0, "today": 0, "goals_minutes": 0, "daily_summary": []}

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
        "text": "⏱️ *Сколько времени я уделил своей цели?*\n_Введи число минут (только цифры):_",
        "input_required": True
    }
]

app = Flask(__name__)

# Простая in-memory база (для Render этого достаточно)
user_states = {}  # {user_id: {"chat_id": ..., "name": ..., "next_question_time": timestamp}}

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """Безопасная отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"❌ Ошибка отправки: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка сети: {e}")
        return False

def send_welcome_message(chat_id, user_name):
    message = f"""🦐 *Я — Mindfulness Криветка!*

Привет, {user_name}! Я буду помогать тебе оставаться осознанным.

Я задаю 2 вопроса по очереди:
1. Ты сейчас сознателен?
2. Сколько времени уделил цели?

⏰ *Расписание:* вопросы приходят с 11:00 до 21:00, каждые 2 часа.

📊 *Все ответы сохраняются* — смотри статистику /stats

Нажми *СТАРТ* чтобы присоединиться!"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 НАЧАТЬ", "callback_data": "start_practice"}]
        ]
    }
    
    return send_telegram_message(chat_id, message, reply_markup=keyboard)

def send_question(chat_id, question_data, user_name="", question_num=1):
    if question_data.get("input_required"):
        message = f"""🦐 *Mindfulness Криветка*

*Вопрос {question_num}:*

{question_data['text']}"""
        
        return send_telegram_message(chat_id, message)
    else:
        keyboard = {"inline_keyboard": []}
        
        for option in question_data["options"]:
            keyboard["inline_keyboard"].append([
                {"text": option["text"], "callback_data": option["callback"]}
            ])
        
        message = f"""🦐 *Mindfulness Криветка*

*Вопрос {question_num}:*

{question_data['text']}

Выбери ответ:"""
        
        return send_telegram_message(chat_id, message, reply_markup=keyboard)

def is_within_schedule():
    """Проверяет, находится ли текущее время в расписании (11:00-21:00)"""
    now = datetime.now()
    current_hour = now.hour
    return 11 <= current_hour < 22

def get_next_schedule_time():
    """Рассчитывает время следующей отправки по расписанию"""
    now = datetime.now()
    current_hour = now.hour
    
    if current_hour < 11:
        next_time = now.replace(hour=11, minute=0, second=0, microsecond=0)
    
    elif current_hour >= 21:
        next_day = now + timedelta(days=1)
        next_time = next_day.replace(hour=11, minute=0, second=0, microsecond=0)
    
    else:
        next_hour = current_hour
        while True:
            next_hour += 1
            if next_hour > 21:
                next_day = now + timedelta(days=1)
                next_time = next_day.replace(hour=11, minute=0, second=0, microsecond=0)
                break
            if next_hour % 2 == 1 and 11 <= next_hour <= 21:
                next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
                break
    
    return next_time

@app.route('/')
def home():
    """Главная страница для проверки работы"""
    now = datetime.now()
    next_time = get_next_schedule_time()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🦐 Mindfulness Криветка</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }}
            h1 {{
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 30px;
            }}
            .status {{
                background: rgba(255, 255, 255, 0.2);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .emoji {{
                font-size: 1.5em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1><span class="emoji">🦐</span> Mindfulness Криветка</h1>
            
            <div class="status">
                <h2>✅ Бот работает</h2>
                <p><strong>Текущее время:</strong> {now.strftime('%H:%M')}</p>
                <p><strong>В расписании:</strong> {'ДА' if is_within_schedule() else 'НЕТ'}</p>
                <p><strong>Следующий вопрос:</strong> {next_time.strftime('%H:%M')}</p>
                <p><strong>Пользователей:</strong> {len(user_states)}</p>
            </div>
            
            <h2>📱 Как использовать:</h2>
            <ol>
                <li>Найдите бота в Telegram</li>
                <li>Напишите <code>/start</code></li>
                <li>Нажмите кнопку <strong>🚀 НАЧАТЬ</strong></li>
                <li>Получайте вопросы с 11:00 до 21:00</li>
                <li>Смотрите статистику: <code>/stats</code></li>
            </ol>
            
            <h2>⏰ Расписание:</h2>
            <ul>
                <li>11:00 — первый вопрос дня</li>
                <li>13:00 — второй вопрос</li>
                <li>15:00 — третий вопрос</li>
                <li>17:00 — четвёртый вопрос</li>
                <li>19:00 — пятый вопрос</li>
                <li>21:00 — последний вопрос</li>
            </ul>
            
            <p style="text-align: center; margin-top: 40px;">
                <small>Бот автоматически перезапускается при ошибках</small>
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check для Render"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "users_count": len(user_states),
        "within_schedule": is_within_schedule()
    }), 200

@app.route('/ping')
def ping():
    """Простой пинг для поддержания активности"""
    return "pong", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Упрощённый обработчик вебхуков"""
    try:
        update = request.get_json()
        
        # Обработка текстовых сообщений
        if 'message' in update and 'text' in update['message']:
            text = update['message']['text']
            chat_id = update['message']['chat']['id']
            user = update['message']['from']
            user_id = user['id']
            user_name = user.get('first_name', 'друг')
            
            logger.info(f"📩 Сообщение от {user_name}: {text}")
            
            # Сохраняем состояние пользователя
            if user_id not in user_states:
                user_states[user_id] = {
                    "chat_id": chat_id,
                    "name": user_name,
                    "waiting_for_time": False,
                    "last_active": datetime.now().isoformat()
                }
            
            # Обработка команд
            if text == '/start':
                send_welcome_message(chat_id, user_name)
                
            elif text == '/stats':
                # Получаем и отправляем статистику
                today_responses = get_today_responses(user_id)
                stats = get_user_stats(user_id, 7)
                
                # Форматируем ответы за сегодня
                if today_responses:
                    today = datetime.now().strftime("%d.%m.%Y")
                    today_text = f"📝 *Ответы за сегодня ({today}):*\n\n"
                    
                    for i, resp in enumerate(today_responses[:10], 1):  # Ограничим 10 ответами
                        time_str = ""
                        if "timestamp" in resp:
                            try:
                                dt = datetime.fromisoformat(resp["timestamp"].replace('Z', '+00:00'))
                                time_str = dt.strftime("%H:%M")
                            except:
                                pass
                        
                        question = resp.get("question", "")
                        answer = resp.get("answer", "")
                        
                        if "Ты сейчас сознателен?" in question:
                            q_short = "Сознателен?"
                        elif "Сколько времени я уделил своей цели?" in question:
                            q_short = "Время на цели"
                        else:
                            q_short = question[:15] + "..."
                        
                        if answer.isdigit():
                            answer_text = f"{answer} мин"
                        else:
                            answer_text = answer
                        
                        today_text += f"{i}. *{time_str}* — {q_short}: {answer_text}\n"
                    
                    send_telegram_message(chat_id, today_text)
                    time.sleep(1)
                
                # Форматируем статистику
                if stats["total"] > 0:
                    summary_text = ""
                    for day in stats["daily_summary"]:
                        date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
                        date_str = date_obj.strftime("%d.%m")
                        summary_text += f"📅 *{date_str}:* {day['responses']} ответов, {day['goals_minutes']} мин на цели\n"
                    
                    total_hours = stats["goals_minutes"] // 60
                    total_minutes = stats["goals_minutes"] % 60
                    
                    stats_text = f"""📊 *Статистика для {user_name}*

*За {stats['period_days']} дней:*
• Ответов: {stats['total']}
• Сегодня: {stats['today']}
• Время на цели: {stats['goals_minutes']} мин ({total_hours} ч {total_minutes} мин)

*Последние 7 дней:*
{summary_text}"""
                    
                    send_telegram_message(chat_id, stats_text)
                else:
                    send_telegram_message(chat_id, f"📊 *Статистика для {user_name}*\n\nНет ответов. Начни практику! 🚀")
                
            elif text == '/help':
                help_text = """🦐 *Помощь*

*Команды:*
/start - начать
/stats - ответы за сегодня + статистика
/help - помощь

*Расписание:*
Вопросы приходят с 11:00 до 21:00, каждые 2 часа.
Вне этого времени бот отдыхает."""
                
                send_telegram_message(chat_id, help_text)
            
            # Если пользователь ждёт ответа на вопрос о времени
            elif user_states[user_id].get("waiting_for_time", False):
                text = text.strip()
                
                if text.isdigit():
                    minutes = int(text)
                    
                    if 0 <= minutes <= 1440:
                        save_response(
                            user_id,
                            user_name,
                            "Сколько времени я уделил своей цели?",
                            f"{minutes}",
                            datetime.now().isoformat(),
                            "text"
                        )
                        
                        user_states[user_id]["waiting_for_time"] = False
                        
                        # Планируем следующий вопрос
                        next_time = get_next_schedule_time()
                        next_time_str = next_time.strftime("%H:%M")
                        user_states[user_id]["next_question_time"] = time.mktime(next_time.timetuple())
                        
                        send_telegram_message(chat_id, 
                            f"✅ {minutes} минут записано.\nСледующий вопрос в *{next_time_str}*")
                    else:
                        send_telegram_message(chat_id, 
                            f"❌ Введи число от 0 до 1440.\nСколько минут?")
                else:
                    send_telegram_message(chat_id, 
                        "❌ Только цифры.\nСколько минут?")
        
        # Обработка нажатий кнопок
        elif 'callback_query' in update:
            callback = update['callback_query']
            user = callback['from']
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            user_id = user['id']
            user_name = user.get('first_name', 'друг')
            
            logger.info(f"🖱️ Кнопка от {user_name}: {callback_data}")
            
            # Ответ на кнопку
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                "callback_query_id": callback['id'],
                "text": "✅",
                "show_alert": False
            })
            
            if callback_data == "start_practice":
                # Инициализируем пользователя
                user_states[user_id] = {
                    "chat_id": chat_id,
                    "name": user_name,
                    "waiting_for_time": False,
                    "last_active": datetime.now().isoformat()
                }
                
                # Отправляем первый вопрос, если время подходящее
                if is_within_schedule():
                    send_question(chat_id, MINDFULNESS_QUESTIONS[0], user_name, 1)
                    
                    # Планируем следующий вопрос
                    next_time = get_next_schedule_time()
                    user_states[user_id]["next_question_time"] = time.mktime(next_time.timetuple())
                    
                    logger.info(f"🚀 Начата практика для {user_name}, следующий вопрос в {next_time.strftime('%H:%M')}")
                else:
                    next_time = get_next_schedule_time()
                    next_time_str = next_time.strftime("%H:%M")
                    send_telegram_message(chat_id, 
                        f"⏰ Сейчас время отдыха (вопросы с 11:00 до 21:00).\nСледующий вопрос в *{next_time_str}*")
                    
                    user_states[user_id]["next_question_time"] = time.mktime(next_time.timetuple())
            
            # Обработка ответов на первый вопрос
            else:
                for question in MINDFULNESS_QUESTIONS:
                    if "options" in question:
                        for option in question["options"]:
                            if option["callback"] == callback_data:
                                save_response(
                                    user_id,
                                    user.get('username', user_name),
                                    question["text"],
                                    option["text"],
                                    datetime.now().isoformat(),
                                    "button"
                                )
                                break
                
                # Отправляем второй вопрос
                time.sleep(1)
                send_question(chat_id, MINDFULNESS_QUESTIONS[1], user_name, 2)
                user_states[user_id]["waiting_for_time"] = True
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка в вебхуке: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/check_schedule', methods=['GET'])
def check_schedule():
    """Проверка и отправка запланированных вопросов"""
    try:
        current_time = time.time()
        sent_count = 0
        
        for user_id, user_data in list(user_states.items()):
            next_time = user_data.get("next_question_time", 0)
            
            # Если время пришло и пользователь не ждёт ответа
            if (current_time >= next_time and 
                not user_data.get("waiting_for_time", False) and
                is_within_schedule()):
                
                send_question(user_data["chat_id"], MINDFULNESS_QUESTIONS[0], user_data["name"], 1)
                sent_count += 1
                
                # Обновляем время следующего вопроса
                next_schedule_time = get_next_schedule_time()
                user_data["next_question_time"] = time.mktime(next_schedule_time.timetuple())
                user_data["last_active"] = datetime.now().isoformat()
        
        return jsonify({
            "status": "ok",
            "sent": sent_count,
            "total_users": len(user_states),
            "time": datetime.now().strftime("%H:%M:%S")
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки расписания: {e}")
        return jsonify({"status": "error"}), 500

def setup_webhook():
    """Настройка вебхука при запуске"""
    try:
        # Удаляем старый вебхук
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
        
        # Устанавливаем новый
        webhook_url = f"https://mindfulness-bot-1.onrender.com/webhook"
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={"url": webhook_url},
            timeout=10
        )
        
        logger.info(f"🌐 Вебхук установлен: {response.json()}")
        
    except Exception as e:
        logger.error(f"⚠️ Ошибка вебхука: {e}")

if __name__ == "__main__":
    # Настраиваем вебхук
    setup_webhook()
    
    now = datetime.now()
    next_time = get_next_schedule_time()
    
    print("\n" + "=" * 60)
    print("🚀 MINDFULNESS КРИВЕТКА ЗАПУЩЕНА")
    print("=" * 60)
    print(f"⏰ Текущее время: {now.strftime('%H:%M:%S')}")
    print(f"📅 Расписание: {'АКТИВНО' if is_within_schedule() else 'НЕАКТИВНО'}")
    print(f"⏰ Следующий вопрос: {next_time.strftime('%H:%M')}")
    print(f"🔗 Веб-интерфейс: https://mindfulness-bot-1.onrender.com")
    print(f"🔗 Вебхук: https://mindfulness-bot-1.onrender.com/webhook")
    print(f"❤️  Health check: https://mindfulness-bot-1.onrender.com/health")
    print(f"🔄 Schedule check: https://mindfulness-bot-1.onrender.com/check_schedule")
    print("=" * 60 + "\n")
    
    # Запускаем Flask
    app.run(
        host='0.0.0.0',
        port=10000,
        debug=False,
        use_reloader=False,
        threaded=True
    )
