"""
ТЕСТОВЫЙ БОТ - проверяет окружение без запуска реального бота
"""
import os
import sys
import subprocess
from datetime import datetime

print("=" * 60)
print("🤖 ТЕСТОВЫЙ БОТ - ДИАГНОСТИКА RENDER")
print("=" * 60)

# Шаг 1: Проверяем, где мы и что вокруг
print("\n1️⃣ ПРОВЕРКА ФАЙЛОВ В ПРОЕКТЕ:")
print("-" * 40)
current_dir = os.getcwd()
print(f"📁 Текущая папка: {current_dir}")

print("\n📂 Список файлов:")
try:
    files = os.listdir('.')
    for file in files:
        file_type = "📄" if os.path.isfile(file) else "📁"
        print(f"   {file_type} {file}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Шаг 2: Проверяем requirements.txt
print("\n2️⃣ ПРОВЕРКА requirements.txt:")
print("-" * 40)
req_file = 'requirements.txt'
if os.path.exists(req_file):
    print(f"✅ Файл '{req_file}' НАЙДЕН")
    
    # Читаем содержимое
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                print(f"📋 Содержимое файла:")
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    print(f"   {i:2d}. {line}")
            else:
                print("⚠️ Файл пустой!")
    except Exception as e:
        print(f"❌ Не могу прочитать файл: {e}")
else:
    print(f"❌ Файл '{req_file}' НЕ НАЙДЕН!")

# Шаг 3: Проверяем установленные пакеты
print("\n3️⃣ ПРОВЕРКА УСТАНОВЛЕННЫХ ПАКЕТОВ:")
print("-" * 40)
try:
    # Проверяем конкретные пакеты
    test_packages = ['flask', 'python-telegram-bot', 'python-dotenv']
    
    for package in test_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - УСТАНОВЛЕН")
        except ImportError:
            print(f"❌ {package} - НЕ УСТАНОВЛЕН")
except Exception as e:
    print(f"⚠️ Ошибка проверки пакетов: {e}")

# Шаг 4: Проверяем переменные окружения
print("\n4️⃣ ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ:")
print("-" * 40)

# Ключи, которые ищем
env_keys = ['BOT_TOKEN', 'CHAT_ID', 'PORT', 'PYTHON_VERSION', 'RENDER']

print("🔍 Поиск переменных окружения:")
for key in env_keys:
    value = os.environ.get(key)
    if value:
        # Маскируем токен для безопасности
        if 'TOKEN' in key:
            masked = value[:10] + '...' if len(value) > 10 else '***'
            print(f"   ✅ {key} = {masked}")
        else:
            print(f"   ✅ {key} = {value}")
    else:
        print(f"   ❌ {key} - НЕ НАЙДЕНА")

# Шаг 5: Проверяем Python и систему
print("\n5️⃣ ИНФОРМАЦИЯ О СИСТЕМЕ:")
print("-" * 40)
print(f"🐍 Python версия: {sys.version}")
print(f"📦 Путь Python: {sys.executable}")
print(f"🕐 Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Шаг 6: Простая проверка Flask
print("\n6️⃣ ТЕСТ FLASK (минимальный):")
print("-" * 40)
try:
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/test')
    def test():
        return "✅ Flask работает!"
    
    print("✅ Flask импортируется без ошибок")
    print("   Сервер НЕ запускается (это только тест)")
except ImportError as e:
    print(f"❌ Ошибка импорта Flask: {e}")
except Exception as e:
    print(f"⚠️ Другая ошибка с Flask: {e}")

print("\n" + "=" * 60)
print("🔚 ТЕСТ ЗАВЕРШЕН")
print("=" * 60)

# ВАЖНО: НЕ запускаем вечный цикл!
print("\n💡 Код завершается. Это нормально для теста.")
print("   Для реального бота нужно app.run() или цикл.")
