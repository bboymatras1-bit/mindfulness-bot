# mindfulness_bot_v5.py - Бот с опросами с 09:00 до 21:00 (Webhook версия)
import time
import threading
import asyncio
import json
import os
from datetime import datetime, date, time as dt_time
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
import requests

# ======== ДОБАВЛЕНО ДЛЯ FLASK И WEBHOOK ========
from flask import Flask, request, Response
app = Flask(__name__)
# ===============================================

def send_poll_to_user_sync(user_id, bot):
    """Синхронная функция для отправки опроса пользователю"""
    try:
        username = user_data.get(str(user_id), {}).get("first_name", "друг")
        
        poll_text = (
            f"🕰️ *Время самопроверки, {username}!*\n\n"
            f"*1. В каком состоянии внимание сейчас?*\n"
            f"   • 👁️ Был внимателен и присутствовал\n"
            f"   • 🤖 Спал и действовал на автомате\n\n"
            f"*2. Помнил ли ты о своей цели?*\n\n"
            f"*3. Сколько минут уделил цели?*\n"
            f"   (0-120 минут)\n\n"
            f"Отвечай по одному вопросу за раз!"
        )
        
        # Сбрасываем состояние пользователя для нового опроса
        user_states[user_id] = {
            "step": 1,
            "data": {}
        }
        
        future = asyncio.run_coroutine_threadsafe(
            bot.bot.send_message(
                chat_id=user_id,
                text=poll_text,
                parse_mode="Markdown",
                reply_markup=state_keyboard
            ),
            loop
        )
        future.result(timeout=10)
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка отправки опроса пользователю {user_id}: {e}")
        if user_id in user_states:
            del user_states[user_id]
        return False

# ================= КОНФИГУРАЦИЯ =================
BOT_TOKEN = "8424450945:AAE6uWv4tlADMTfH-rUNojYEIUVqwTei9JY"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # URL для вебхука

# Настройки
POLL_INTERVAL = 7200  # 7200 секунд = 2 часа
START_HOUR = 9        # Начало опросов в 09:00
END_HOUR = 21         # Конец опросов в 21:00
# ================================================

# Глобальные переменные
active_users = set()
bot_instance = None
timer_thread = None
scheduler_thread = None
stop_timer = False
loop = None
user_states = {}
user_data = {}
DATA_FILE = "user_data.json"

# Клавиатура для состояния
state_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("👁️ Был внимателен и присутствовал")],
    [KeyboardButton("🤖 Спал и действовал на автомате")],
    [KeyboardButton("➡️ Пропустить комментарий")]
], resize_keyboard=True, one_time_keyboard=True)

# Клавиатура для вопроса о цели
goal_remember_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("✅ Да"), KeyboardButton("❌ Нет")],
    [KeyboardButton("➡️ Пропустить комментарий")]
], resize_keyboard=True, one_time_keyboard=True)

def load_user_data():
    """Загружает данные пользователей из файла"""
    global user_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            print(f"✅ Загружены данные {len(user_data)} пользователей")
        else:
            user_data = {}
            print("📁 Файл данных не найден, создаю новый")
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        user_data = {}

def save_user_data():
    """Сохраняет данные пользователей в файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены")
    except Exception as e:
        print(f"❌ Ошибка сохранения данных: {e}")

def add_user_record(user_id, record):
    """Добавляет запись для пользователя"""
    today = date.today().isoformat()
    
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            "username": "",
            "first_name": "",
            "records": {}
        }
    
    if today not in user_data[str(user_id)]["records"]:
        user_data[str(user_id)]["records"][today] = []
    
    record["timestamp"] = datetime.now().isoformat()
    user_data[str(user_id)]["records"][today].append(record)
    
    save_user_data()
    return record

def get_today_stats(user_id):
    """Возвращает статистику за сегодня"""
    today = date.today().isoformat()
    user_id_str = str(user_id)
    
    if user_id_str not in user_data or today not in user_data[user_id_str]["records"]:
        return None
    
    records = user_data[user_id_str]["records"][today]
    
    stats = {
        "total_polls": len(records),
        "present_states": sum(1 for r in records if r.get("state") == "👁️ Был внимателен и присутствовал"),
        "autopilot_states": sum(1 for r in records if r.get("state") == "🤖 Спал и действовал на автомате"),
        "remembered_goal": sum(1 for r in records if r.get("remembered_goal") == "✅ Да"),
        "goals_with_text": sum(1 for r in records if r.get("goal_text", "").strip() != ""),
        "states_with_comment": sum(1 for r in records if r.get("state_comment", "").strip() != ""),
        "goals_with_comment": sum(1 for r in records if r.get("goal_comment", "").strip() != ""),
        "total_minutes": sum(r.get("minutes", 0) for r in records),
        "records": records
    }
    
    return stats

def is_active_time():
    """Проверяет, находится ли текущее время в диапазоне 09:00-21:00"""
    now = datetime.now()
    current_hour = now.hour
    return START_HOUR <= current_hour < END_HOUR

def get_next_poll_time():
    """Возвращает время следующего опроса"""
    now = datetime.now()
    current_hour = now.hour
    
    if current_hour >= END_HOUR or current_hour < START_HOUR:
        tomorrow = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        tomorrow = tomorrow.replace(day=tomorrow.day + 1)
        return tomorrow
    else:
        seconds_since_9am = (current_hour - START_HOUR) * 3600 + now.minute * 60 + now.second
        intervals_passed = seconds_since_9am // POLL_INTERVAL
        next_interval = intervals_passed + 1
        next_seconds_from_9am = next_interval * POLL_INTERVAL
        
        next_hours = START_HOUR + (next_seconds_from_9am // 3600)
        remaining_seconds = next_seconds_from_9am % 3600
        next_minutes = remaining_seconds // 60
        next_seconds = remaining_seconds % 60
        
        next_time = now.replace(hour=next_hours, minute=next_minutes, second=next_seconds, microsecond=0)
        
        if next_time.hour >= END_HOUR:
            tomorrow = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
            tomorrow = tomorrow.replace(day=tomorrow.day + 1)
            return tomorrow
        
        if next_time <= now:
            next_seconds_from_9am += POLL_INTERVAL
            next_hours = START_HOUR + (next_seconds_from_9am // 3600)
            remaining_seconds = next_seconds_from_9am % 3600
            next_minutes = remaining_seconds // 60
            next_seconds = remaining_seconds % 60
            next_time = now.replace(hour=next_hours, minute=next_minutes, second=next_seconds, microsecond=0)
        
        return next_time

def send_polls_periodically():
    """Функция в отдельном потоке для отправки опросов (только 09:00-21:00)"""
    global stop_timer, bot_instance, active_users, loop
    
    print(f"⏰ Таймер опросов запущен (интервал: {POLL_INTERVAL//3600} часа, время: {START_HOUR}:00-{END_HOUR}:00)")
    
    last_poll_time = None
    
    while not stop_timer:
        current_time = time.time()
        now = datetime.now()
        current_hour = now.hour
        
        if START_HOUR <= current_hour < END_HOUR:
            seconds_since_9am = (current_hour - START_HOUR) * 3600 + now.minute * 60 + now.second
            
            if seconds_since_9am % POLL_INTERVAL == 0:
                current_poll_time = (now.hour, now.minute)
                if current_poll_time != last_poll_time:
                    if active_users and bot_instance:
                        try:
                            print(f"[{now.strftime('%H:%M:%S')}] Отправляю опрос {len(active_users)} пользователям")
                            
                            users_to_poll = list(active_users)
                            
                            for user_id in users_to_poll:
                                success = send_poll_to_user_sync(user_id, bot_instance)
                                if success:
                                    print(f"  ✅ Опрос отправлен пользователю {user_id}")
                                else:
                                    active_users.discard(user_id)
                                    print(f"  🗑️ Удалён пользователь {user_id} (ошибка отправки)")
                            
                            last_poll_time = current_poll_time
                            
                        except Exception as e:
                            print(f"❌ Ошибка в таймере опросов: {e}")
        else:
            last_poll_time = None
            
            if current_hour >= END_HOUR:
                next_poll = get_next_poll_time()
                time_until_next = (next_poll - now).total_seconds()
                hours_until = int(time_until_next // 3600)
                minutes_until = int((time_until_next % 3600) // 60)
                
                if hours_until > 0 or minutes_until > 10:
                    print(f"🌙 Ночное время ({now.strftime('%H:%M')}). Следующий опрос завтра в {START_HOUR}:00 ({hours_until}ч {minutes_until}мин)")
                    time.sleep(600)
                else:
                    time.sleep(30)
            elif current_hour < START_HOUR:
                next_poll = get_next_poll_time()
                time_until_next = (next_poll - now).total_seconds()
                hours_until = int(time_until_next // 3600)
                minutes_until = int((time_until_next % 3600) // 60)
                
                if hours_until > 0 or minutes_until > 10:
                    print(f"🌙 Утреннее время ({now.strftime('%H:%M')}). Опросы начнутся в {START_HOUR}:00 ({hours_until}ч {minutes_until}мин)")
                    time.sleep(600)
                else:
                    time.sleep(30)
        
        time.sleep(1)

def send_daily_summary():
    """Отправляет ежедневную сводку в 21:00"""
    global bot_instance, loop
    
    if not bot_instance or not active_users:
        return
    
    print(f"📊 Отправляю ежедневные сводки в {END_HOUR}:00...")
    
    for user_id in list(active_users):
        try:
            stats = get_today_stats(user_id)
            
            if stats and stats["total_polls"] > 0:
                present_percent = (stats["present_states"] / stats["total_polls"] * 100) if stats["total_polls"] > 0 else 0
                goal_percent = (stats["remembered_goal"] / stats["total_polls"] * 100) if stats["total_polls"] > 0 else 0
                text_percent = (stats["goals_with_text"] / stats["remembered_goal"] * 100) if stats["remembered_goal"] > 0 else 0
                
                summary = (
                    f"📊 *ЕЖЕДНЕВНАЯ СВОДКА*\n"
                    f"*Время: {END_HOUR}:00*\n\n"
                    f"• Всего опросов: {stats['total_polls']}\n"
                    f"• 👁️ Было присутствия: {stats['present_states']} ({present_percent:.0f}%)\n"
                    f"• 🤖 Было на автопилоте: {stats['autopilot_states']}\n"
                    f"• Помнил о цели: {stats['remembered_goal']} раз ({goal_percent:.0f}%)\n"
                    f"• Записал цели: {stats['goals_with_text']} раз ({text_percent:.0f}%)\n"
                    f"• Время на цели: {stats['total_minutes']} мин ({stats['total_minutes']/60:.1f} ч)\n\n"
                )
                
                if stats["states_with_comment"] > 0:
                    summary += f"📝 *Комментарии к состояниям:* {stats['states_with_comment']} записей\n"
                
                if stats["goals_with_text"] > 0:
                    summary += "\n🎯 *Записанные цели:*\n"
                    for record in stats["records"]:
                        if record.get("goal_text"):
                            goal_text = record["goal_text"]
                            summary += f"• {goal_text}\n"
                            if record.get("goal_comment"):
                                summary += f"  *Комментарий:* {record['goal_comment']}\n"
                
                summary += f"\n🌙 *Опросы завершены до завтра {START_HOUR}:00*\nСпокойной ночи!"
                
                future = asyncio.run_coroutine_threadsafe(
                    bot_instance.bot.send_message(
                        chat_id=user_id,
                        text=summary,
                        parse_mode="Markdown"
                    ),
                    loop
                )
                future.result(timeout=10)
                print(f"  📊 Сводка отправлена пользователю {user_id}")
                
        except Exception as e:
            print(f"  ❌ Ошибка отправки сводки пользователю {user_id}: {e}")

def scheduler():
    """Планировщик для ежедневных задач"""
    global stop_timer
    
    print(f"📅 Планировщик запущен (сводка в {END_HOUR}:00)")
    
    while not stop_timer:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        if current_hour == END_HOUR and current_minute == 0:
            send_daily_summary()
            time.sleep(60)
        
        time.sleep(30)

# ======== FLASK И WEBHOOK ========
@app.route('/')
def index():
    """Простая страница для проверки работы"""
    return "🤖 Mindfulness Bot работает! ✅"

@app.route('/health')
def health():
    """Health check endpoint"""
    return "OK", 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook_legacy():
    """Старый endpoint для вебхука (для обратной совместимости)"""
    return webhook()

@app.route(f'/webhook', methods=['POST'])
def webhook():
    """Основной endpoint для вебхука от Telegram"""
    if request.method == "POST":
        try:
            # Получаем данные от Telegram
            update_data = request.get_json()
            
            if update_data:
                update_id = update_data.get('update_id', 'unknown')
                print(f"📩 Получено обновление #{update_id}")
                
                # Создаем Update объект
                update = Update.de_json(update_data, bot_instance.bot if bot_instance else None)
                
                # Обрабатываем обновление в асинхронном цикле
                if update and bot_instance:
                    # Используем run_coroutine_threadsafe для обработки
                    future = asyncio.run_coroutine_threadsafe(
                        process_update_async(update),
                        loop
                    )
                    
                    # Ждем результат с таймаутом
                    try:
                        future.result(timeout=5)
                    except asyncio.TimeoutError:
                        print(f"⚠️ Таймаут обработки обновления #{update_id}")
                    except Exception as e:
                        print(f"❌ Ошибка при ожидании результата: {e}")
                
                return 'ok', 200
            else:
                print("⚠️ Пустое обновление")
                return 'no data', 400
            
        except Exception as e:
            print(f"❌ Ошибка в вебхуке: {e}")
            import traceback
            traceback.print_exc()
            return f'error: {str(e)}', 400
    
    return 'method not allowed', 405

async def process_update_async(update):
    """Асинхронная обработка обновления"""
    try:
        if bot_instance:
            await bot_instance.process_update(update)
    except Exception as e:
        print(f"❌ Ошибка обработки обновления: {e}")
        import traceback
        traceback.print_exc()

def set_webhook():
    """Устанавливает вебхук на сервере Telegram"""
    try:
        if not WEBHOOK_URL:
            print("⚠️ WEBHOOK_URL не указан, не могу установить вебхук")
            print("💡 Для локального тестирования установите:")
            print("   export WEBHOOK_URL=https://ваш-ngrok-url.ngrok.io")
            return False
        
        webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        print(f"🔗 Устанавливаю webhook: {webhook_url}")
        
        # Сначала удаляем старый webhook
        delete_url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook'
        try:
            delete_response = requests.get(delete_url, timeout=10)
            print(f"🗑️ Удаление старого webhook: {delete_response.json().get('description', 'OK')}")
        except Exception as e:
            print(f"⚠️ Не удалось удалить старый webhook: {e}")
        
        # Ждем немного
        time.sleep(1)
        
        # Устанавливаем новый webhook
        set_url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
        set_data = {
            'url': webhook_url,
            'max_connections': 100,
            'allowed_updates': ['message', 'callback_query', 'chat_member']
        }
        
        try:
            response = requests.post(set_url, json=set_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print(f"✅ Webhook установлен успешно!")
                    print(f"📝 Description: {result.get('description', 'N/A')}")
                    return True
                else:
                    print(f"❌ Ошибка установки webhook: {result}")
                    return False
            else:
                print(f"❌ Ошибка HTTP при установке webhook: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ Таймаут при установке webhook")
            return False
        except Exception as e:
            print(f"❌ Ошибка при установке webhook: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка при установке webhook: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_webhook_info():
    """Получает информацию о текущем webhook"""
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo'
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                webhook_info = result.get('result', {})
                print(f"📊 Информация о webhook:")
                print(f"   URL: {webhook_info.get('url', 'N/A')}")
                print(f"   Has custom certificate: {webhook_info.get('has_custom_certificate', 'N/A')}")
                print(f"   Pending update count: {webhook_info.get('pending_update_count', 'N/A')}")
                print(f"   Last error date: {webhook_info.get('last_error_date', 'N/A')}")
                print(f"   Last error message: {webhook_info.get('last_error_message', 'N/A')}")
                return webhook_info
        return None
    except Exception as e:
        print(f"❌ Ошибка получения информации о webhook: {e}")
        return None

def check_webhook():
    """Проверяет, правильно ли настроен webhook"""
    try:
        webhook_info = get_webhook_info()
        if webhook_info:
            url = webhook_info.get('url', '')
            if url and WEBHOOK_URL and WEBHOOK_URL in url:
                print(f"✅ Webhook настроен правильно: {url}")
                return True
            else:
                print(f"⚠️ Webhook настроен на другой URL: {url}")
                print(f"💡 Ожидался URL содержащий: {WEBHOOK_URL}")
                return False
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки webhook: {e}")
        return False
# ================================================

# Все функции обработки команд (start_command, handle_state_response и т.д.)
# остаются БЕЗ ИЗМЕНЕНИЙ, как в предыдущем коде
# Я сокращу их для читаемости, но в реальном коде они должны быть полностью

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - подписаться на опросы"""
    global timer_thread, bot_instance, loop, scheduler_thread
    
    user = update.effective_user
    user_id = user.id
    
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            "username": user.username or "",
            "first_name": user.first_name or "",
            "records": {}
        }
        save_user_data()
    
    if bot_instance is None:
        bot_instance = context.application
        loop = asyncio.get_event_loop()
    
    active_users.add(user_id)
    
    if timer_thread is None or not timer_thread.is_alive():
        global stop_timer
        stop_timer = False
        timer_thread = threading.Thread(target=send_polls_periodically, daemon=True)
        timer_thread.start()
        print("⏰ Таймер опросов запущен!")
    
    if scheduler_thread is None or not scheduler_thread.is_alive():
        scheduler_thread = threading.Thread(target=scheduler, daemon=True)
        scheduler_thread.start()
        print("📅 Планировщик запущен!")
    
    now = datetime.now()
    current_hour = now.hour
    
    welcome_msg = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"✅ *Ты подписан на опросы самосознания!*\n\n"
        f"📅 *Расписание опросов:*\n"
        f"• С {START_HOUR}:00 до {END_HOUR}:00\n"
        f"• Каждые {POLL_INTERVAL//3600} часа\n\n"
        f"🎯 *Что спрашиваю:*\n"
        f"1. Состояние внимания (👁️/🤖)\n"
        f"2. Помнил ли о цели (✅/❌)\n"
        f"3. Время на цели (0-120 мин)\n\n"
    )
    
    if START_HOUR <= current_hour < END_HOUR:
        next_poll = get_next_poll_time()
        time_until_next = (next_poll - now).total_seconds()
        hours_until = int(time_until_next // 3600)
        minutes_until = int((time_until_next % 3600) // 60)
        
        welcome_msg += f"⏰ *Сейчас дневное время*\n"
        welcome_msg += f"Следующий опрос через {hours_until}ч {minutes_until}мин\n\n"
    else:
        if current_hour >= END_HOUR:
            welcome_msg += f"🌙 *Сейчас ночное время*\n"
            welcome_msg += f"Опросы начнутся завтра в {START_HOUR}:00\n\n"
        else:
            time_until_start = (now.replace(hour=START_HOUR, minute=0, second=0) - now).total_seconds()
            hours_until = int(time_until_start // 3600)
            minutes_until = int((time_until_start % 3600) // 60)
            
            welcome_msg += f"🌅 *Сейчас утреннее время*\n"
            welcome_msg += f"Первый опрос сегодня в {START_HOUR}:00 ({hours_until}ч {minutes_until}мин)\n\n"
    
    welcome_msg += (
        f"📊 *Ежедневно в {END_HOUR}:00:*\n"
        f"• Итоговая статистика\n"
        f"• Сводка по целям\n\n"
        f"👥 *Активных подписчиков:* {len(active_users)}\n\n"
        f"**Команды:**\n"
        f"🛑 `/stop` - отписаться\n"
        f"📊 `/stats` - статистика\n"
        f"📝 `/manual` - добавить запись\n"
        f"⏰ `/next_poll` - когда следующий опрос\n"
        f"📋 `/help` - справка"
    )
    
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")
    print(f"➕ Добавлен пользователь {user_id} ({user.first_name})")

async def next_poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /next_poll - показать время следующего опроса"""
    now = datetime.now()
    next_poll = get_next_poll_time()
    time_until_next = (next_poll - now).total_seconds()
    
    hours_until = int(time_until_next // 3600)
    minutes_until = int((time_until_next % 3600) // 60)
    
    if time_until_next > 3600:
        time_text = f"{hours_until} часов {minutes_until} минут"
    elif time_until_next > 60:
        time_text = f"{minutes_until} минут"
    else:
        time_text = "менее минуты"
    
    await update.message.reply_text(
        f"⏰ *Время следующего опроса:*\n\n"
        f"• *Когда:* {next_poll.strftime('%H:%M')}\n"
        f"• *Через:* {time_text}\n"
        f"• *Расписание:* {START_HOUR}:00-{END_HOUR}:00\n\n"
        f"📅 *Сегодняшние опросы:*\n"
        f"• {START_HOUR}:00, 11:00, 13:00, 15:00, 17:00, 19:00",
        parse_mode="Markdown"
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stop - отписаться от опросов"""
    user = update.effective_user
    user_id = user.id
    
    if user_id in active_users:
        active_users.remove(user_id)
        remaining = len(active_users)
        
        await update.message.reply_text(
            f"🛑 {user.first_name}, ты отписался от опросов.\n"
            f"Осталось подписчиков: {remaining}\n\n"
            f"Напиши `/start` чтобы вернуться!",
            parse_mode="Markdown"
        )
        print(f"➖ Удалён пользователь {user_id}")
    else:
        await update.message.reply_text(
            "😊 Ты и так не подписан.\n"
            "Напиши `/start` чтобы присоединиться!",
            parse_mode="Markdown"
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика за сегодня"""
    user_id = update.effective_user.id
    stats = get_today_stats(user_id)
    
    if not stats or stats["total_polls"] == 0:
        await update.message.reply_text(
            "📊 *Сегодня ещё нет записей.*\n\n"
            f"⏰ *Расписание опросов:*\n"
            f"• С {START_HOUR}:00 до {END_HOUR}:00\n"
            f"• Каждые {POLL_INTERVAL//3600} часа\n\n"
            f"📅 *Сегодняшние опросы:*\n"
            f"• {START_HOUR}:00, 11:00, 13:00, 15:00, 17:00, 19:00",
            parse_mode="Markdown"
        )
        return
    
    present_percent = (stats["present_states"] / stats["total_polls"] * 100) if stats["total_polls"] > 0 else 0
    goal_percent = (stats["remembered_goal"] / stats["total_polls"] * 100) if stats["total_polls"] > 0 else 0
    text_percent = (stats["goals_with_text"] / stats["remembered_goal"] * 100) if stats["remembered_goal"] > 0 else 0
    
    report = (
        f"📊 *СТАТИСТИКА ЗА СЕГОДНЯ*\n\n"
        f"• Всего опросов: {stats['total_polls']}\n"
        f"• 👁️ Было присутствия: {stats['present_states']} ({present_percent:.0f}%)\n"
        f"• 🤖 Было на автопилоте: {stats['autopilot_states']}\n"
        f"• Помнил о цели: {stats['remembered_goal']} раз ({goal_percent:.0f}%)\n"
        f"• Записал цели: {stats['goals_with_text']} раз ({text_percent:.0f}%)\n"
        f"• Время на цели: {stats['total_minutes']} мин ({stats['total_minutes']/60:.1f} ч)\n\n"
    )
    
    if stats["states_with_comment"] > 0:
        report += "📝 *Комментарии к состояниям:*\n"
        for record in stats["records"]:
            if record.get("state_comment"):
                time_str = datetime.fromisoformat(record["timestamp"]).strftime("%H:%M")
                report += f"• *{time_str}* ({record['state']}): {record['state_comment']}\n"
        report += "\n"
    
    if stats["goals_with_text"] > 0:
        report += "🎯 *Записанные цели:*\n"
        for record in stats["records"]:
            if record.get("goal_text"):
                time_str = datetime.fromisoformat(record["timestamp"]).strftime("%H:%M")
                report += f"• *{time_str}*: {record['goal_text']}\n"
                if record.get("goal_comment"):
                    report += f"  *Комментарий:* {record['goal_comment']}\n"
        report += "\n"
    
    if present_percent >= 70:
        report += "🎯 *Отличная осознанность!* Ты часто присутствовал.\n"
    elif present_percent >= 40:
        report += "👍 *Хороший баланс.* Заметил и присутствие, и автопилот.\n"
    else:
        report += "💡 *Автопилот преобладает.* Просто замечай когда ты не здесь.\n"
    
    if goal_percent >= 70:
        report += "🎯 *Отличная фокусировка на цели!*"
        if text_percent >= 50:
            report += " И даже записываешь их!"
    elif goal_percent >= 40:
        report += "💪 *Цель в фокусе.* Продолжай в том же духе!"
    else:
        report += "🤔 *Цель теряется.* Напомни себе о ней."
    
    now = datetime.now()
    if START_HOUR <= now.hour < END_HOUR:
        next_poll = get_next_poll_time()
        time_until_next = (next_poll - now).total_seconds()
        hours_until = int(time_until_next // 3600)
        minutes_until = int((time_until_next % 3600) // 60)
        
        if hours_until > 0 or minutes_until > 0:
            report += f"\n\n⏰ *Следующий опрос через {hours_until}ч {minutes_until}мин*"
    else:
        report += f"\n\n🌙 *На сегодня опросы завершены*\nСледующий опрос завтра в {START_HOUR}:00"
    
    await update.message.reply_text(report, parse_mode="Markdown")
    print(f"📊 Статистика отправлена пользователю {user_id}")

async def manual_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /manual - добавить запись вручную"""
    user_id = update.effective_user.id
    
    user_states[user_id] = {
        "step": 1,
        "data": {"manual": True}
    }
    
    await update.message.reply_text(
        "📝 *Ручное добавление записи*\n\n"
        "1. *В каком состоянии внимание сейчас?*",
        parse_mode="Markdown",
        reply_markup=state_keyboard
    )

async def test_poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test_poll - получить опрос сейчас"""
    user_id = update.effective_user.id
    
    if user_id in active_users:
        success = send_poll_to_user_sync(user_id, bot_instance)
        if success:
            await update.message.reply_text(
                "🧪 *Тестовый опрос отправлен!*\n"
                "Проверяй сообщения от бота.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Не удалось отправить опрос")
    else:
        await update.message.reply_text(
            "Сначала подпишись через `/start`",
            parse_mode="Markdown"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка"""
    help_text = (
        f"📋 *СПРАВКА ПО КОМАНДАМ*\n\n"
        f"`/start` - подписаться на опросы ({START_HOUR}:00-{END_HOUR}:00)\n"
        f"`/stop` - отписаться от опросов\n"
        f"`/stats` - статистика за сегодня\n"
        f"`/manual` - добавить запись вручную\n"
        f"`/next_poll` - когда следующий опрос\n"
        f"`/test_poll` - получить опрос прямо сейчас\n"
        f"`/help` - эта справка\n\n"
        f"*Расписание опросов:*\n"
        f"• С {START_HOUR}:00 до {END_HOUR}:00\n"
        f"• Каждые {POLL_INTERVAL//3600} часа\n\n"
        f"📅 *Примерное расписание:*\n"
        f"• {START_HOUR}:00, 11:00, 13:00, 15:00, 17:00, 19:00\n\n"
        f"📊 *Ежедневно в {END_HOUR}:00:*\n"
        f"• Итоговая статистика\n"
        f"• Сводка по целям"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def handle_state_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа на вопрос о состоянии"""
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]["step"] != 1:
        return
    
    state = update.message.text
    
    if state not in ["👁️ Был внимателен и присутствовал", "🤖 Спал и действовал на автомате", "➡️ Пропустить комментарий"]:
        await update.message.reply_text(
            "⚠️ Пожалуйста, выбери один из вариантов:",
            reply_markup=state_keyboard
        )
        return
    
    if state == "➡️ Пропустить комментарий":
        await update.message.reply_text(
            "👌 Понял, пропускаем.\n\n"
            "Выбери состояние внимания:",
            reply_markup=state_keyboard
        )
        return
    
    user_states[user_id]["data"]["state"] = state
    user_states[user_id]["step"] = 2
    
    await update.message.reply_text(
        f"✅ *{state}* - записал.\n\n"
        f"*Хочешь добавить комментарий к состоянию?*\n"
        f"(Например: 'Был сконцентрирован на работе', 'Мечтал о будущем', 'Автоматически делал рутину')\n\n"
        f"Если не хочешь, отправь '➡️ Пропустить комментарий'",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("➡️ Пропустить комментарий")]
        ], resize_keyboard=True, one_time_keyboard=True)
    )

async def handle_state_comment_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария к состоянию"""
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]["step"] != 2:
        return
    
    comment = update.message.text.strip()
    
    if comment == "➡️ Пропустить комментарий" or comment == "":
        user_states[user_id]["data"]["state_comment"] = ""
    else:
        user_states[user_id]["data"]["state_comment"] = comment
    
    user_states[user_id]["step"] = 3
    
    await update.message.reply_text(
        "👌 *Понял.*\n\n"
        "*2. Помнил ли ты о своей цели в последние 2 часа?*",
        parse_mode="Markdown",
        reply_markup=goal_remember_keyboard
    )

async def handle_goal_remember_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа на вопрос 'Помнил ли о цели?'"""
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]["step"] != 3:
        return
    
    remembered = update.message.text
    
    if remembered not in ["✅ Да", "❌ Нет", "➡️ Пропустить комментарий"]:
        await update.message.reply_text(
            "⚠️ Пожалуйста, выбери один из вариантов:",
            reply_markup=goal_remember_keyboard
        )
        return
    
    if remembered == "➡️ Пропустить комментарий":
        await update.message.reply_text(
            "👌 Понял, пропускаем.\n\n"
            "Помнил ли ты о своей цели в последние 2 часа?",
            reply_markup=goal_remember_keyboard
        )
        return
    
    user_states[user_id]["data"]["remembered_goal"] = remembered
    user_states[user_id]["step"] = 4
    
    await update.message.reply_text(
        f"✅ *{remembered}* - записал.\n\n"
        f"*Хочешь добавить комментарий о цели?*\n"
        f"(Например: 'Цель была чёткой', 'Смутно помнил', 'Полностью забыл')\n\n"
        f"Если не хочешь, отправь '➡️ Пропустить комментарий'",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("➡️ Пропустить комментарий")]
        ], resize_keyboard=True, one_time_keyboard=True)
    )

async def handle_goal_comment_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария о цели"""
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]["step"] != 4:
        return
    
    comment = update.message.text.strip()
    
    if comment == "➡️ Пропустить комментарий" or comment == "":
        user_states[user_id]["data"]["goal_comment"] = ""
    else:
        user_states[user_id]["data"]["goal_comment"] = comment
    
    if user_states[user_id]["data"]["remembered_goal"] == "✅ Да":
        user_states[user_id]["step"] = 5
        
        await update.message.reply_text(
            "🎯 *Отлично!*\n\n"
            "*Теперь напиши свои цели, если помнишь о них.*\n"
            "(Можешь написать кратко, например: 'Изучить Python', 'Сделать проект', 'Поработать над здоровьем')\n\n"
            "Если не хочешь писать, просто отправь '—'",
            parse_mode="Markdown",
            reply_markup=None
        )
    else:
        user_states[user_id]["data"]["goal_text"] = ""
        user_states[user_id]["step"] = 6
        
        await update.message.reply_text(
            "👌 *Понял.*\n\n"
            "*3. Сколько минут уделил цели?*\n"
            "(От 0 до 120, просто отправь число)\n\n"
            "*Примечание:* Даже если не помнил о цели, мог быть прогресс!",
            parse_mode="Markdown",
            reply_markup=None
        )

async def handle_goal_text_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста цели"""
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]["step"] != 5:
        return
    
    goal_text = update.message.text.strip()
    
    user_states[user_id]["data"]["goal_text"] = goal_text if goal_text != "—" else ""
    user_states[user_id]["step"] = 6
    
    if goal_text and goal_text != "—":
        await update.message.reply_text(
            f"📝 *Цель записана:* {goal_text[:50]}\n\n"
            f"*3. Сколько минут уделил цели?*\n"
            f"(От 0 до 120, просто отправь число)",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "👌 *Понял.*\n\n"
            "*3. Сколько минут уделил цели?*\n"
            "(От 0 до 120, просто отправь число)",
            parse_mode="Markdown"
        )

async def handle_minutes_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа на вопрос о времени"""
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]["step"] != 6:
        return
    
    try:
        minutes = int(update.message.text)
        if minutes < 0 or minutes > 120:
            await update.message.reply_text("⚠️ Введи число от 0 до 120")
            return
        
        user_states[user_id]["data"]["minutes"] = minutes
        record = add_user_record(user_id, user_states[user_id]["data"])
        
        state_emoji = "👁️" if record["state"] == "👁️ Был внимателен и присутствовал" else "🤖"
        
        report = f"{state_emoji} *Запись сохранена!*\n\n"
        report += f"• *Состояние:* {record['state']}\n"
        
        if record.get("state_comment"):
            report += f"  *Комментарий:* {record['state_comment']}\n"
        
        report += f"• *Помнил о цели:* {record.get('remembered_goal', '—')}\n"
        
        if record.get("goal_comment"):
            report += f"  *Комментарий:* {record['goal_comment']}\n"
        
        if record.get("goal_text"):
            report += f"• *Текст цели:* {record['goal_text']}\n"
        
        report += f"• *Время на цель:* {minutes} мин\n"
        report += f"• *Время:* {datetime.now().strftime('%H:%M')}\n\n"
        
        now = datetime.now()
        next_poll = get_next_poll_time()
        
        if now.hour >= END_HOUR:
            report += f"🌙 *На сегодня опросы завершены.*\n"
            report += f"Следующий опрос завтра в {START_HOUR}:00\n\n"
            report += f"📊 В {END_HOUR}:00 получишь ежедневную сводку!"
        else:
            time_until_next = (next_poll - now).total_seconds()
            hours_until = int(time_until_next // 3600)
            minutes_until = int((time_until_next % 3600) // 60)
            
            report += f"⏰ Следующий опрос через {hours_until}ч {minutes_until}мин\n"
        
        report += "/stats - посмотреть статистику"
        
        await update.message.reply_text(report, parse_mode="Markdown")
        print(f"📝 Запись сохранена для пользователя {user_id}")
        
        del user_states[user_id]
        
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, введи число (например: 45)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех текстовых сообщений"""
    user_id = update.effective_user.id
    
    if user_id in user_states:
        step = user_states[user_id]["step"]
        
        if step == 1:
            await handle_state_response(update, context)
        elif step == 2:
            await handle_state_comment_response(update, context)
        elif step == 3:
            await handle_goal_remember_response(update, context)
        elif step == 4:
            await handle_goal_comment_response(update, context)
        elif step == 5:
            await handle_goal_text_response(update, context)
        elif step == 6:
            await handle_minutes_response(update, context)
        return
    
    await update.message.reply_text(
        "🤔 Не понял запрос.\n"
        "Используй команды:\n"
        "• `/start` - подписаться на опросы\n"
        "• `/stats` - статистика\n"
        "• `/manual` - добавить запись вручную\n"
        "• `/next_poll` - когда следующий опрос\n"
        "• `/help` - справка\n"
        "• `/stop` - отписаться",
        parse_mode="Markdown"
    )

def check_token():
    """Проверяет токен"""
    if not BOT_TOKEN or "ТВОЙ_ТОКЕН_ЗДЕСЬ" in BOT_TOKEN:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не указан токен бота!")
        print("\n📱 Как получить токен:")
        print("1. Открой Telegram")
        print("2. Найди @BotFather")
        print("3. Отправь /newbot")
        print("4. Придумай имя бота")
        print("5. Скопируй токен")
        print("6. Вставь токен в переменную BOT_TOKEN")
        return False
    return True

def setup_bot():
    """Настраивает бота и возвращает приложение"""
    global loop
    
    app_bot = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    app_bot.add_handler(CommandHandler("start", start_command))
    app_bot.add_handler(CommandHandler("stop", stop_command))
    app_bot.add_handler(CommandHandler("stats", stats_command))
    app_bot.add_handler(CommandHandler("manual", manual_command))
    app_bot.add_handler(CommandHandler("test_poll", test_poll_command))
    app_bot.add_handler(CommandHandler("next_poll", next_poll_command))
    app_bot.add_handler(CommandHandler("help", help_command))
    
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return app_bot

def run_webhook_mode():
    """Запускает бота в режиме webhook"""
    global bot_instance, loop
    
    print("🌐 Запускаю в режиме WEBHOOK")
    
    # Настраиваем бота
    app_bot = setup_bot()
    bot_instance = app_bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Инициализируем бота
    print("🤖 Инициализирую бота...")
    app_bot.initialize()
    
    # Запускаем таймеры в отдельном потоке
    global stop_timer
    stop_timer = False
    
    timer_thread = threading.Thread(target=send_polls_periodically, daemon=True)
    timer_thread.start()
    
    scheduler_thread = threading.Thread(target=scheduler, daemon=True)
    scheduler_thread.start()
    
    # Устанавливаем webhook
    if set_webhook():
        print("✅ Webhook успешно установлен")
    else:
        print("❌ Не удалось установить webhook")
        print("💡 Попробуйте вручную установить webhook:")
        print(f"   curl -X POST https://api.telegram.org/bot{BOT_TOKEN}/setWebhook -d 'url={WEBHOOK_URL}/{BOT_TOKEN}'")
    
    # Проверяем информацию о webhook
    check_webhook()
    
    return app_bot

def run_polling_mode():
    """Запускает бота в режиме polling"""
    global bot_instance, loop
    
    print("📡 Запускаю в режиме POLLING")
    
    # Настраиваем бота
    app_bot = setup_bot()
    bot_instance = app_bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Запускаем таймеры в отдельном потоке
    global stop_timer
    stop_timer = False
    
    timer_thread = threading.Thread(target=send_polls_periodically, daemon=True)
    timer_thread.start()
    
    scheduler_thread = threading.Thread(target=scheduler, daemon=True)
    scheduler_thread.start()
    
    return app_bot

def main():
    """Главная функция"""
    print("🤖" + "="*50)
    print(f"🤖 МИНДФУЛНЕС БОТ - ОПРОСЫ {START_HOUR}:00-{END_HOUR}:00")
    print("🤖" + "="*50)
    
    load_user_data()
    
    if not check_token():
        return
    
    print(f"✅ Токен: {BOT_TOKEN[:10]}...")
    print(f"⏰ Расписание: {START_HOUR}:00-{END_HOUR}:00")
    print(f"📅 Интервал: {POLL_INTERVAL//3600} часа")
    print(f"📊 Загружено пользователей: {len(user_data)}")
    print(f"🎯 Примерное расписание: {START_HOUR}:00, 11:00, 13:00, 15:00, 17:00, 19:00")
    
    try:
        # Проверяем, нужно ли использовать webhook
        port = os.environ.get("PORT")
        webhook_url = os.environ.get("WEBHOOK_URL")
        
        if port and webhook_url:
            # Режим webhook (для Render/Heroku)
            print(f"🌐 Запуск в режиме WEBHOOK")
            print(f"🔗 Webhook URL: {webhook_url}")
            print(f"🚀 Порт: {port}")
            
            # Запускаем бота в режиме webhook
            run_webhook_mode()
            
            print("\n✅ Бот работает в режиме webhook!")
            print("📩 Ожидаю обновления от Telegram...")
            print(f"📝 Webhook URL: {webhook_url}/{BOT_TOKEN}")
            
            # Запускаем Flask
            app.run(
                host='0.0.0.0', 
                port=int(port), 
                debug=False, 
                use_reloader=False,
                threaded=True
            )
            
        else:
            # Режим polling (для локальной разработки)
            print("💻 Запуск в режиме POLLING (локально)")
            
            app_bot = run_polling_mode()
            
            print("\n✅ Бот инициализирован")
            print(f"\n📋 Команды в Telegram:")
            print(f"  /start     - подписаться на опросы")
            print(f"  /stop      - отписаться")
            print(f"  /stats     - статистика за сегодня")
            print(f"  /manual    - добавить запись вручную")
            print(f"  /next_poll - когда следующий опрос")
            print(f"  /test_poll - получить опрос сейчас")
            print(f"  /help      - справка по командам")
            print(f"\n⏰ Опросы: {START_HOUR}:00-{END_HOUR}:00")
            print(f"📅 Каждые: {POLL_INTERVAL//3600} часа")
            print(f"📊 Сводка: ежедневно в {END_HOUR}:00")
            print("\n" + "="*50)
            print("⚠️ Для остановки нажмите Ctrl+C")
            print("="*50)
            
            # Запускаем polling
            app_bot.run_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
        global stop_timer
        stop_timer = True
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

# ======== ГЛАВНЫЙ ЗАПУСК ========
if __name__ == "__main__":
    main()
