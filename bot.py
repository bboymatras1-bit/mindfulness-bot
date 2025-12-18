# mindfulness_bot_v5.py - Бот с опросами с 09:00 до 21:00
import time
import threading
import asyncio
import json
import os
from datetime import datetime, date, time as dt_time
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request
import logging

# ================= КОНФИГУРАЦИЯ =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")  # БЕРЕМ ТОКЕН ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ!
# ================================================

# Настройки
POLL_INTERVAL = 7200  # 7200 секунд = 2 часа
START_HOUR = 9
END_HOUR = 21

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

# Flask приложение
app = Flask(__name__)
telegram_app = None  # Будет хранить экземпляр Telegram Application

# ... ВАШ ОРИГИНАЛЬНЫЙ КОД БОТА (без изменений) ...
# ВСТАВЬТЕ СЮДА ВСЕ ФУНКЦИИ ИЗ ВАШЕГО ИСХОДНОГО ФАЙЛА:
# load_user_data(), save_user_data(), add_user_record(), 
# get_today_stats(), is_active_time(), get_next_poll_time(),
# send_polls_periodically(), send_daily_summary(), scheduler(),
# handle_state_response(), handle_state_comment_response(),
# handle_goal_remember_response(), handle_goal_comment_response(),
# handle_goal_text_response(), handle_minutes_response(),
# start_command(), stop_command(), stats_command(), 
# manual_command(), test_poll_command(), help_command(), 
# next_poll_command(), handle_message(), check_token()
# ... Вставьте ВСЕ эти функции без изменений ...

# ======== КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: функция main() ========
def main():
    """Инициализация и запуск бота"""
    global telegram_app, bot_instance, loop
    
    print("="*60)
    print(f"🤖 МИНДФУЛНЕС БОТ - ОПРОСЫ {START_HOUR}:00-{END_HOUR}:00")
    print("="*60)
    
    # Проверка токена
    if not BOT_TOKEN:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не указан токен бота!")
        print("Добавьте переменную BOT_TOKEN в настройки Render")
        return None
    
    print(f"✅ Токен: {BOT_TOKEN[:10]}...")
    print(f"⏰ Расписание: {START_HOUR}:00-{END_HOUR}:00")
    
    try:
        # Создаем приложение Telegram
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        
        # Сохраняем для использования в других функциях
        bot_instance = telegram_app.bot
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Регистрируем команды
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("stop", stop_command))
        telegram_app.add_handler(CommandHandler("stats", stats_command))
        telegram_app.add_handler(CommandHandler("manual", manual_command))
        telegram_app.add_handler(CommandHandler("test_poll", test_poll_command))
        telegram_app.add_handler(CommandHandler("next_poll", next_poll_command))
        telegram_app.add_handler(CommandHandler("help", help_command))
        
        from telegram.ext import MessageHandler, filters
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот инициализирован")
        print("📋 Доступные команды: /start, /stop, /stats, /help")
        
        # Загружаем данные
        load_user_data()
        
        # Запускаем фоновые потоки
        global stop_timer, timer_thread, scheduler_thread
        stop_timer = False
        
        if timer_thread is None or not timer_thread.is_alive():
            timer_thread = threading.Thread(target=send_polls_periodically, daemon=True)
            timer_thread.start()
            print("⏰ Таймер опросов запущен")
        
        if scheduler_thread is None or not scheduler_thread.is_alive():
            scheduler_thread = threading.Thread(target=scheduler, daemon=True)
            scheduler_thread.start()
            print("📅 Планировщик запущен")
        
        return telegram_app
        
    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        import traceback
        traceback.print_exc()
        return None

# ======== Flask endpoints ========
@app.route('/')
def home():
    return "✅ Mindfulness Bot is running (Webhook mode)"

@app.route('/', methods=['POST'])
def webhook():
    """Endpoint для вебхука от Telegram"""
    if telegram_app:
        try:
            update_data = request.get_json()
            # Создаем Update объект
            update = Update.de_json(update_data, telegram_app.bot)
            # Запускаем обработку в потоке
            telegram_app.update_queue.put_nowait(update)
            return 'ok'
        except Exception as e:
            print(f"❌ Ошибка обработки вебхука: {e}")
            return 'error', 500
    return 'bot not initialized', 503

@app.route('/health')
def health():
    return "OK", 200

# ======== Запуск приложения ========
def run_bot_in_background():
    """Запускает бота в фоновом режиме"""
    global telegram_app
    print("🤖 Starting Telegram bot in background...")
    
    # Инициализируем бота
    app_instance = main()
    if not app_instance:
        print("❌ Bot initialization failed")
        return
    
    telegram_app = app_instance
    
    # Запускаем polling в отдельном потоке
    def start_polling():
        print("🔄 Starting bot polling...")
        try:
            telegram_app.run_polling()
        except Exception as e:
            print(f"❌ Bot polling stopped: {e}")
    
    poll_thread = threading.Thread(target=start_polling, daemon=True)
    poll_thread.start()
    
    print("✅ Telegram bot started successfully")

if __name__ == "__main__":
    # Запускаем бота в фоне
    bot_thread = threading.Thread(target=run_bot_in_background, daemon=True)
    bot_thread.start()
    
    # Даем время на инициализацию
    time.sleep(5)
    
    # Определяем порт для Render
    port = int(os.environ.get("PORT", 10000))
    
    # Проверяем, запущены ли мы на Render
    is_render = os.environ.get("RENDER") == "true"
    
    print(f"🌐 Starting web server on port {port}...")
    print(f"🔧 Render environment: {is_render}")
    
    if is_render:
        # Используем Waitress для production на Render
        from waitress import serve
        serve(app, host="0.0.0.0", port=port)
    else:
        # Для локальной разработки
        app.run(host="0.0.0.0", port=port, debug=False)
