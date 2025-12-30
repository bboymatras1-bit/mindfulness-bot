import os
import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import requests
import re

print("=" * 50)
print("🤖 MINDFULNESS КРИВЕТКА")
print("=" * 50)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен: {BOT_TOKEN[:10]}...")

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
        
        print(f"💾 Ответ: {user_id} -> {answer}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def get_today_responses(user_id):
    """Получает все ответы пользователя за сегодня"""
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
        
        # Сортируем по времени (от новых к старым)
        today_responses.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return today_responses
    except Exception as e:
        print(f"❌ Ошибка получения ответов за сегодня: {e}")
        return []

def get_user_stats(user_id, period_days=7):
    if not os.path.exists(DB_FILE):
        return {"total": 0, "today": 0, "conscious": 0, "goals_minutes": 0, "daily_summary": []}
    
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
        
        conscious = sum(1 for r in user_responses if "сознателен" in r.get("answer", ""))
        
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
            conscious_count = sum(1 for r in date_responses if "сознателен" in r.get("answer", ""))
            
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
        print(f"❌ Ошибка статистики: {e}")
        return {"total": 0, "today": 0, "conscious": 0, "goals_minutes": 0, "daily_summary": []}

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

user_sessions = {}
question_schedule = {}
awaiting_time_response = {}
current_question_index = {}

def send_welcome_message(chat_id, user_name):
    message = f"""🦐 *Я — Mindfulness Криветка!*

Привет, {user_name}! Я буду помогать тебе оставаться осознанным.

Каждые *2 часа* я задаю 2 вопроса по очереди:
1. Ты сейчас сознателен?
2. Сколько времени уделил цели?

📊 *Все ответы сохраняются* — смотри статистику /stats

Нажми *СТАРТ* для начала!"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 НАЧАТЬ", "callback_data": "start_practice"}]
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
        print(f"👋 Приветствие {user_name}")
        return response.status_code == 200
    except:
        return False

def send_question(chat_id, question_data, user_name="", question_num=1):
    if question_data.get("input_required"):
        message = f"""🦐 *Mindfulness Криветка*

*Вопрос {question_num}:*

{question_data['text']}"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if user_name:
                print(f"⏱️ Вопрос {question_num} {user_name}")
            return True
        except:
            return False
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
                print(f"🦐 Вопрос {question_num} {user_name}")
            return response.status_code == 200
        except:
            return False

def format_stats_message(stats, user_name):
    """Форматирует статистику"""
    if stats["total"] == 0:
        return f"""📊 *Статистика для {user_name}*

Нет ответов. Начни практику! 🚀"""
    
    summary_text = ""
    for day in stats["daily_summary"]:
        date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m")
        summary_text += f"📅 *{date_str}:* {day['responses']} ответов, {day['conscious']} осознанных, {day['goals_minutes']} мин на цели\n"
    
    total_hours = stats["goals_minutes"] // 60
    total_minutes = stats["goals_minutes"] % 60
    
    return f"""📊 *Статистика для {user_name}*

*За {stats['period_days']} дней:*
• Ответов: {stats['total']}
• Сегодня: {stats['today']}
• Осознанных: {stats['conscious']}
• Осознанность: {stats['conscious_percent']:.1f}%
• Время на цели: {stats['goals_minutes']} мин ({total_hours} ч {total_minutes} мин)

*Последние 7 дней:*
{summary_text}"""

def format_today_responses(today_responses):
    """Форматирует ответы за сегодня"""
    if not today_responses:
        return "📝 *Ответы за сегодня:*\n\nПока нет ответов за сегодня."
    
    today = datetime.now().strftime("%d.%m.%Y")
    result = f"📝 *Ответы за сегодня ({today}):*\n\n"
    
    for i, response in enumerate(today_responses, 1):
        time_str = ""
        if "timestamp" in response:
            try:
                dt = datetime.fromisoformat(response["timestamp"].replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except:
                time_str = response.get("date", "").split()[1] if " " in response.get("date", "") else ""
        
        question = response.get("question", "")
        answer = response.get("answer", "")
        
        # Упрощаем вопросы для отображения
        if "Ты сейчас сознателен?" in question:
            q_short = "Сознателен?"
        elif "Сколько времени я уделил своей цели?" in question:
            q_short = "Время на цели"
        else:
            q_short = question[:20] + "..." if len(question) > 20 else question
        
        # Форматируем ответ
        if answer.isdigit():
            answer_text = f"{answer} мин"
        else:
            answer_text = answer
        
        result += f"{i}. *{time_str}* — {q_short}: {answer_text}\n"
    
    return result

@app.route('/')
def home():
    return """<h1>🦐 Mindfulness Криветка</h1><p>Бот работает. Напиши /start в Telegram</p>"""

@app.route('/health')
def health():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        
        if 'message' in update and 'text' in update['message']:
            text = update['message']['text']
            chat_id = update['message']['chat']['id']
            user = update['message']['from']
            user_id = user['id']
            user_name = user.get('first_name', 'друг')
            
            print(f"📩 {user_name}: {text}")
            
            if user_id in awaiting_time_response and awaiting_time_response[user_id]:
                handle_time_input(chat_id, user_id, user_name, text)
                return jsonify({"status": "ok"}), 200
            
            if text == '/start':
                send_welcome_message(chat_id, user_name)
                user_sessions[chat_id] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "waiting_for_start": True
                }
                print(f"🦐 Новый {user_name}")
                
            elif text == '/stats':
                # Получаем ответы за сегодня
                today_responses = get_today_responses(user_id)
                
                if today_responses:
                    # Отправляем ответы за сегодня
                    today_message = format_today_responses(today_responses)
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": today_message,
                        "parse_mode": "Markdown"
                    })
                    
                    # Пауза 1 секунда
                    time.sleep(1)
                
                # Отправляем общую статистику
                stats = get_user_stats(user_id, 7)
                stats_message = format_stats_message(stats, user_name)
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": stats_message,
                    "parse_mode": "Markdown"
                })
                
            elif text.startswith('/stats'):
                parts = text.split()
                if len(parts) > 1 and parts[1].isdigit():
                    # Получаем ответы за сегодня
                    today_responses = get_today_responses(user_id)
                    
                    if today_responses:
                        today_message = format_today_responses(today_responses)
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": today_message,
                            "parse_mode": "Markdown"
                        })
                        
                        time.sleep(1)
                    
                    period = min(int(parts[1]), 365)
                    stats = get_user_stats(user_id, period)
                    stats_message = format_stats_message(stats, user_name)
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": stats_message,
                        "parse_mode": "Markdown"
                    })
                else:
                    # Просто /stats без параметра
                    today_responses = get_today_responses(user_id)
                    
                    if today_responses:
                        today_message = format_today_responses(today_responses)
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": today_message,
                            "parse_mode": "Markdown"
                        })
                        
                        time.sleep(1)
                    
                    stats = get_user_stats(user_id, 7)
                    stats_message = format_stats_message(stats, user_name)
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": stats_message,
                        "parse_mode": "Markdown"
                    })
                    
            elif text == '/help':
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": """🦐 *Помощь*

*Команды:*
/start - начать
/stats - ответы за сегодня + статистика
/stats N - ответы за сегодня + статистика за N дней
/help - помощь

*Как работает:*
1. Нажми НАЧАТЬ
2. Отвечай на вопросы по очереди
3. Каждые 2 часа новые вопросы
4. Все ответы сохраняются
5. Смотри историю в /stats""",
                    "parse_mode": "Markdown"
                })
        
        elif 'callback_query' in update:
            callback = update['callback_query']
            user = callback['from']
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            user_name = user.get('first_name', 'друг')
            user_id = user['id']
            
            print(f"🖱️ {user_name}: {callback_data}")
            
            if callback_data == "start_practice":
                send_first_question(chat_id, user_id, user_name)
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": callback['id'],
                    "text": "Начинаем!",
                    "show_alert": False
                })
            else:
                handle_first_question_response(callback, chat_id, user_id, user_name)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"status": "error"}), 500

def send_first_question(chat_id, user_id, user_name):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            "user_id": user_id,
            "user_name": user_name
        }
    
    send_question(chat_id, MINDFULNESS_QUESTIONS[0], user_name, 1)
    current_question_index[user_id] = 0
    question_schedule[chat_id] = time.time() + 7200
    
    print(f"🚀 Первый вопрос отправлен {user_name}")

def handle_first_question_response(callback, chat_id, user_id, user_name):
    callback_data = callback['data']
    
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
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
        "callback_query_id": callback['id'],
        "text": "✅ Записано",
        "show_alert": False
    })
    
    time.sleep(1)
    send_question(chat_id, MINDFULNESS_QUESTIONS[1], user_name, 2)
    awaiting_time_response[user_id] = True
    current_question_index[user_id] = 1
    
    print(f"🦐 Второй вопрос отправлен {user_name}")

def handle_time_input(chat_id, user_id, user_name, text):
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
            
            awaiting_time_response[user_id] = False
            if user_id in current_question_index:
                del current_question_index[user_id]
            
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ {minutes} минут записано. Следующие вопросы через 2 часа.",
                "parse_mode": "Markdown"
            })
        else:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"❌ Введи число от 0 до 1440.\nСколько минут?",
                "parse_mode": "Markdown"
            })
    else:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": "❌ Только цифры.\nСколько минут?",
            "parse_mode": "Markdown"
        })

def send_scheduled_questions():
    while True:
        try:
            current_time = time.time()
            
            for chat_id, next_time in list(question_schedule.items()):
                if current_time >= next_time and chat_id in user_sessions:
                    session = user_sessions[chat_id]
                    user_id = session["user_id"]
                    
                    if user_id in awaiting_time_response and awaiting_time_response[user_id]:
                        continue
                    
                    send_question(chat_id, MINDFULNESS_QUESTIONS[0], session["user_name"], 1)
                    current_question_index[user_id] = 0
                    question_schedule[chat_id] = current_time + 7200
                    
                    print(f"🕐 Вопросы по расписанию {session['user_name']}")
            
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Ошибка планировщика: {e}")
            time.sleep(30)

def setup_webhook():
    try:
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        requests.post(delete_url, timeout=5)
        print("🗑️ Вебхук удалён")
        
        webhook_url = f"https://mindfulness-bot-1.onrender.com/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        
        response = requests.post(set_url, json={"url": webhook_url}, timeout=10)
        print(f"🌐 Вебхук: {response.json()}")
        
    except Exception as e:
        print(f"⚠️ Вебхук: {e}")

if __name__ == "__main__":
    setup_webhook()
    
    scheduler_thread = threading.Thread(target=send_scheduled_questions, daemon=True)
    scheduler_thread.start()
    
    print("🚀 Запуск...")
    print(f"🔗 https://mindfulness-bot-1.onrender.com")
    print("🤖 Напиши /start в Telegram")
    print("📊 /stats показывает ответы за сегодня и статистику")
    
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
