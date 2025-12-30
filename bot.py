import os
import time
import json
import threading
from datetime import datetime
import requests

print("=" * 50)
print("🤖 MINDFULNESS КРИВЕТКА")
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

# 4. Функции для Telegram API
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

# 5. Класс для управления сессиями
class MindfulnessBot:
    def __init__(self):
        self.user_sessions = {}  # {chat_id: {...}}
        self.question_schedule = {}  # {chat_id: next_time}
        self.last_update_id = 0
        
        # Очищаем старые обновления
        self.cleanup_old_updates()
        
    def cleanup_old_updates(self):
        """Удаляет старые обновления из очереди Telegram"""
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            response = requests.get(url, params={"offset": -1}, timeout=5)
            print("🧹 Очередь обновлений очищена")
        except:
            pass
    
    def process_update(self, update):
        """Обрабатывает одно обновление"""
        update_id = update.get('update_id', 0)
        
        # Обновляем last_update_id
        if update_id > self.last_update_id:
            self.last_update_id = update_id
        
        # Команда /start или сообщение
        if 'message' in update and 'text' in update['message']:
            self.handle_message(update['message'])
        
        # Обработка нажатий кнопок (включая кнопку Старт)
        elif 'callback_query' in update:
            self.handle_callback(update['callback_query'])
    
    def handle_message(self, message):
        """Обрабатывает текстовые сообщения"""
        text = message['text']
        chat_id = message['chat']['id']
        user = message['from']
        user_name = user.get('first_name', 'друг')
        
        print(f"📩 Сообщение от {user_name}: {text}")
        
        if text == '/start':
            self.handle_start_command(chat_id, user)
        elif text == '/stats':
            self.handle_stats(chat_id, user)
        elif text == '/help':
            self.handle_help(chat_id)
        elif text == '/question':
            # Команда для тестирования - отправляет вопрос сразу
            self.send_first_question(chat_id, user)
    
    def handle_start_command(self, chat_id, user):
        """Обрабатывает команду /start"""
        user_name = user.get('first_name', 'Друг')
        
        # Отправляем приветственное сообщение с кнопкой Старт
        send_welcome_message(chat_id, user_name)
        
        # Регистрируем пользователя, но не планируем автоматический вопрос
        self.user_sessions[chat_id] = {
            "user_id": user['id'],
            "user_name": user_name,
            "question_index": 0,
            "start_time": time.time(),
            "waiting_for_start": True  # Флаг, что ждём нажатия кнопки Старт
        }
        
        print(f"🦐 Новый пользователь: {user_name} (ID: {chat_id})")
        print(f"👥 Всего пользователей: {len(self.user_sessions)}")
    
    def handle_callback(self, callback):
        """Обрабатывает нажатия кнопок"""
        user = callback['from']
        chat_id = callback['message']['chat']['id']
        callback_data = callback['data']
        user_name = user.get('first_name', 'друг')
        
        print(f"🖱️ Кнопка от {user_name}: {callback_data}")
        
        # Если нажата кнопка "СТАРТ"
        if callback_data == "start_practice":
            self.start_practice_for_user(chat_id, user)
            return
        
        # Обработка ответов на вопросы
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
    
    def start_practice_for_user(self, chat_id, user):
        """Начинает практику для пользователя - отправляет первый вопрос"""
        user_name = user.get('first_name', 'Друг')
        
        if chat_id not in self.user_sessions:
            # Если пользователь не зарегистрирован, регистрируем
            self.user_sessions[chat_id] = {
                "user_id": user['id'],
                "user_name": user_name,
                "question_index": 0,
                "start_time": time.time()
            }
        
        # Убираем флаг ожидания старта
        if "waiting_for_start" in self.user_sessions[chat_id]:
            self.user_sessions[chat_id]["waiting_for_start"] = False
        
        # Отправляем первый вопрос
        question_index = self.user_sessions[chat_id]["question_index"]
        question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
        
        if send_mindfulness_question(chat_id, question, user_name):
            print(f"🚀 Первый вопрос отправлен {user_name}")
            
            # Планируем следующий вопрос через 2 часа
            self.question_schedule[chat_id] = time.time() + 7200
            
            # Переходим к следующему вопросу
            self.user_sessions[chat_id]["question_index"] = question_index + 1
        else:
            print(f"❌ Не удалось отправить вопрос {user_name}")
        
        # Подтверждаем нажатие кнопки
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback['id'],
            "text": "Начинаем практику!",
            "show_alert": False
        })
    
    def send_first_question(self, chat_id, user):
        """Отправляет первый вопрос (для команды /question)"""
        user_name = user.get('first_name', 'Друг')
        
        if chat_id not in self.user_sessions:
            # Регистрируем пользователя
            self.user_sessions[chat_id] = {
                "user_id": user['id'],
                "user_name": user_name,
                "question_index": 0,
                "start_time": time.time()
            }
        
        # Отправляем первый вопрос
        question_index = self.user_sessions[chat_id]["question_index"]
        question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
        
        if send_mindfulness_question(chat_id, question, user_name):
            print(f"🚀 Вопрос по команде отправлен {user_name}")
            
            # Планируем следующий вопрос через 2 часа
            self.question_schedule[chat_id] = time.time() + 7200
            
            # Переходим к следующему вопросу
            self.user_sessions[chat_id]["question_index"] = question_index + 1
    
    def handle_stats(self, chat_id, user):
        """Обрабатывает команду /stats"""
        stats = get_user_stats(user['id'])
        user_name = user.get('first_name', 'Друг')
        
        if stats["total"] == 0:
            message = f"📊 *Статистика для {user_name}*\n\nПока нет ответов. Начни практику!"
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
    
    def handle_help(self, chat_id):
        """Обрабатывает команду /help"""
        help_text = """🦐 *Mindfulness Криветка - Помощь*

Доступные команды:
/start - начать работу с ботом
/stats - посмотреть свою статистику
/help - эта справка
/question - получить вопрос немедленно

После начала практики бот будет задавать вопросы каждые 2 часа."""
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": help_text,
            "parse_mode": "Markdown"
        })
    
    def send_scheduled_questions(self):
        """Отправляет запланированные вопросы"""
        current_time = time.time()
        
        for chat_id, next_time in list(self.question_schedule.items()):
            if current_time >= next_time and chat_id in self.user_sessions:
                session = self.user_sessions[chat_id]
                
                # Проверяем, что пользователь уже начал практику
                if session.get("waiting_for_start", False):
                    continue  # Пропускаем, если ждёт нажатия кнопки Старт
                
                # Выбираем вопрос
                question_index = session["question_index"]
                question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
                
                # Отправляем вопрос
                if send_mindfulness_question(chat_id, question, session["user_name"]):
                    print(f"🦐 Вопрос по расписанию для {session['user_name']}")
                    
                    # Обновляем расписание
                    self.question_schedule[chat_id] = current_time + 7200  # 2 часа
                    
                    # Переходим к следующему вопросу
                    self.user_sessions[chat_id]["question_index"] = question_index + 1
                else:
                    print(f"❌ Ошибка отправки для {session['user_name']}")
    
    def run(self):
        """Основной цикл бота"""
        print("🔄 Бот запущен и работает...")
        
        while True:
            try:
                # 1. Получаем обновления
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
                params = {
                    "offset": self.last_update_id + 1,
                    "timeout": 25,
                    "allowed_updates": ["message", "callback_query"]
                }
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('result'):
                        for update in data['result']:
                            self.process_update(update)
                
                # 2. Отправляем запланированные вопросы
                self.send_scheduled_questions()
                
                # 3. Логируем статус раз в минуту
                if int(time.time()) % 60 == 0:
                    active_users = len([s for s in self.user_sessions.values() if not s.get("waiting_for_start", False)])
                    print(f"📊 Статус: {len(self.user_sessions)} пользователей, {active_users} активных")
                
                time.sleep(0.1)
                
            except requests.exceptions.Timeout:
                # Это нормально для long polling
                pass
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                time.sleep(5)

# 6. Простой HTTP сервер для Render
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Простая HTML страница
            html = """<!DOCTYPE html>
<html>
<head>
    <title>🦐 Mindfulness Криветка</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Arial', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .emoji {
            font-size: 24px;
        }
        code {
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        .stats {
            background: #e8f4f8;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><span class="emoji">🦐</span> Mindfulness Криветка</h1>
        <p>Бот для практики осознанности, который помогает оставаться в моменте.</p>
        
        <div class="stats">
            <h3>📊 Статус бота:</h3>
            <p><span class="emoji">✅</span> Бот работает и готов к общению!</p>
        </div>
        
        <h3>🎯 Как начать:</h3>
        <ol>
            <li>Найдите бота в Telegram: <code>@mindfulness_shrimp_bot</code></li>
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
        
        <h3>📞 Поддержка:</h3>
        <p>Если возникли вопросы, свяжитесь с разработчиком.</p>
        
        <p style="text-align: center; margin-top: 30px; color: #666;">
            <small>Mindfulness Криветка © 2025</small>
        </p>
    </div>
</body>
</html>"""
            
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование
        pass

def run_http_server():
    """Запускает простой HTTP сервер"""
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    print(f"🌐 HTTP сервер запущен на порту 10000")
    print(f"🔗 Доступно по: https://mindfulness-bot-1.onrender.com")
    server.serve_forever()

# 7. Запуск
if __name__ == "__main__":
    # Запускаем бота
    bot = MindfulnessBot()
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=bot.run, daemon=True)
    bot_thread.start()
    
    # Запускаем HTTP сервер в основном потоке
    run_http_server()
