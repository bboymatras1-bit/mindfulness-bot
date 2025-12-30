import os
import sys
import time
from multiprocessing import Process
from datetime import datetime

print("=" * 50)
print("🤖 БОТ: MULTIPROCESSING РЕШЕНИЕ")
print("=" * 50)

# 1. Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...")

# 2. Flask сервер в отдельном ПРОЦЕССЕ
def run_flask_process():
    """Flask в отдельном процессе"""
    from flask import Flask
    
    flask_app = Flask(__name__)
    
    @flask_app.route('/')
    def home():
        return "🤖 Бот работает! Напиши /start в Telegram"
    
    @flask_app.route('/health')
    def health():
        return "OK", 200
    
    @flask_app.route('/ping')
    def ping():
        return f"pong: {datetime.now().strftime('%H:%M:%S')}", 200
    
    print("[FLASK] Процесс запущен")
    flask_app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# 3. Telegram бот в отдельном ПРОЦЕССЕ
def run_telegram_process():
    """Telegram бот в отдельном процессе"""
    import asyncio
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        print(f"📨 /start от {user.id} ({user.first_name})")
        await update.message.reply_text(
            f"✅ Привет, {user.first_name}!\n"
            f"Бот работает на Render с multiprocessing!"
        )
    
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📋 /start, /help, /ping")
    
    async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = datetime.now().strftime("%H:%M:%S")
        await update.message.reply_text(f"🏓 Pong! {now}")
    
    async def main():
        print("[TELEGRAM] Инициализирую бота...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping_command))
        
        print("[TELEGRAM] Бот готов. Ожидание команд...")
        await application.run_polling()
    
    print("[TELEGRAM] Процесс запущен")
    asyncio.run(main())

# 4. Главная функция - запуск всего
def main():
    print("🚀 Запускаю процессы...")
    
    # Запускаем Flask в отдельном процессе
    flask_process = Process(target=run_flask_process, daemon=True)
    flask_process.start()
    print("✅ Flask процесс запущен")
    
    time.sleep(3)  # Даём Flask время запуститься
    
    # Запускаем Telegram бота в основном процессе
    # (теперь у каждого процесса свой event loop)
    try:
        run_telegram_process()
    except KeyboardInterrupt:
        print("\n🛑 Остановка бота...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        print("🔚 Завершение работы")

# 5. Точка входа
if __name__ == "__main__":
    # Важно для multiprocessing на Windows/Linux
    if sys.platform.startswith('win'):
        # На Windows нужен этот код
        from multiprocessing import freeze_support
        freeze_support()
    
    main()
