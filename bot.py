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

# 2. База данных (ваш код без изменений)
DB_FILE = "mindfulness_responses.json"
# ... (остальные функции save_response, get_user_stats без изменений)

# 3. Вопросы (ваш код без изменений)
MINDFULNESS_QUESTIONS = [
    # ... (ваши вопросы без изменений)
]

# 4. Функции для Telegram API (ваш код без изменений, но с улучшениями)
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
        response = requests.post(url, json=payload, timeout=10)
        print(f"✅ Вступление отправлено {user_name}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def send_mindfulness_question(chat_id, question_data):
    """Отправляет вопрос с кнопками"""
    keyboard = {"inline_keyboard": []}
    
    for option in question_data["options"]:
        keyboard["inline_keyboard"].append([
            {"text": option["text"], "callback_data": option["callback"]}
        ])
    
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
        
        # Команда /start
        if 'message' in update and 'text' in update['message']:
            self.handle_message(update['message'])
        
        # Обработка нажатий кнопок
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
            self.handle_start(chat_id, user)
        elif text == '/stats':
            self.handle_stats(chat_id, user)
        elif text == '/help':
            self.handle_help(chat_id)
    
    def handle_start(self, chat_id, user):
        """Обрабатывает команду /start"""
        user_name = user.get('first_name', 'Друг')
        
        # Проверяем, нет ли уже сессии
        if chat_id in self.user_sessions:
            print(f"⚠️ {user_name} уже зарегистрирован")
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"Привет снова, {user_name}! Ты уже зарегистрирован. Следующий вопрос по расписанию.",
                "parse_mode": "Markdown"
            })
            return
        
        # Регистрируем нового пользователя
        send_intro_message(chat_id, user_name)
        
        self.user_sessions[chat_id] = {
            "user_id": user['id'],
            "user_name": user_name,
            "question_index": 0,
            "start_time": time.time()
        }
        
        # Первый вопрос через 2 минуты
        self.question_schedule[chat_id] = time.time() + 120
        
        print(f"🦐 Новый пользователь: {user_name} (ID: {chat_id})")
        print(f"👥 Всего пользователей: {len(self.user_sessions)}")
    
    def handle_stats(self, chat_id, user):
        """Обрабатывает команду /stats"""
        stats = get_user_stats(user['id'])
        user_name = user.get('first_name', 'Друг')
        
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
    
    def handle_help(self, chat_id):
        """Обрабатывает команду /help"""
        help_text = """🦐 *Mindfulness Криветка - Помощь*

Доступные команды:
/start - начать работу с ботом
/stats - посмотреть свою статистику
/help - эта справка

Бот задаёт вопросы каждые 2 часа.
Просто нажимай на кнопки под сообщениями!"""
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": help_text,
            "parse_mode": "Markdown"
        })
    
    def handle_callback(self, callback):
        """Обрабатывает нажатия кнопок"""
        user = callback['from']
        chat_id = callback['message']['chat']['id']
        callback_data = callback['data']
        user_name = user.get('first_name', 'друг')
        
        print(f"🖱️ Кнопка от {user_name}: {callback_data}")
        
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
    
    def send_scheduled_questions(self):
        """Отправляет запланированные вопросы"""
        current_time = time.time()
        
        for chat_id, next_time in list(self.question_schedule.items()):
            if current_time >= next_time and chat_id in self.user_sessions:
                session = self.user_sessions[chat_id]
                
                # Выбираем вопрос
                question_index = session["question_index"]
                question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
                
                # Отправляем вопрос
                if send_mindfulness_question(chat_id, question):
                    print(f"🦐 Вопрос для {session['user_name']}: {question['text'][:30]}...")
                    
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
                    print(f"📊 Статус: {len(self.user_sessions)} пользователей")
                
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
</head>
<body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
    <h1>🦐 Mindfulness Криветка</h1>
    <p>Бот для практики осознанности. Задаёт вопросы каждые 2 часа.</p>
    
    <h3>📊 Статус бота:</h3>
    <p>✅ Бот работает и слушает сообщения...</p>
    
    <h3>🎯 Как использовать:</h3>
    <ol>
        <li>Найдите бота в Telegram: <code>@mindfulness_shrimp_bot</code></li>
        <li>Напишите <code>/start</code></li>
        <li>Получайте вопросы каждые 2 часа</li>
        <li>Отвечайте нажимая кнопки</li>
    </ol>
    
    <h3>📞 Контакты:</h3>
    <p>Если есть вопросы, напишите разработчику.</p>
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
