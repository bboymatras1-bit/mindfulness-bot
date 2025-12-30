import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ================== ENV ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ Переменная окружения BOT_TOKEN не установлена")

PORT = int(os.getenv("PORT", 10000))  # Render сам задаёт PORT

# ================== HTTP SERVER (для Render Web Service) ==================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def start_http_server():
    server = HTTPServer(("", PORT), HealthHandler)
    server.serve_forever()

# ================== TELEGRAM HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я простой Telegram-бот, запущенный на Render 🚀"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong!")

# =========
