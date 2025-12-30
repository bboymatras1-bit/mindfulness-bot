# ... (остальной код без изменений)

# УДАЛИТЕ Flask части и используйте ТОЛЬКО этот код:

def bot_main_loop():
    """Основной цикл отправки вопросов - Long Polling версия"""
    print("⏰ Запускаю Mindfulness Криветку...")
    print("📱 Напиши боту /start в Telegram")
    
    user_sessions = {}
    question_schedule = {}
    last_update_id = 0  # Ключевое: храним ID последнего обработанного обновления
    
    while True:
        try:
            # 1. Получаем обновления с offset
            updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": last_update_id + 1}
            
            response = requests.get(updates_url, params=params, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result'):
                    for update in data['result']:
                        update_id = update.get('update_id', 0)
                        last_update_id = max(last_update_id, update_id)  # Обновляем последний ID
                        
                        # Команда /start
                        if 'message' in update and 'text' in update['message']:
                            text = update['message']['text']
                            chat_id = update['message']['chat']['id']
                            user = update['message']['from']
                            
                            if text == '/start':
                                send_intro_message(chat_id, user.get('first_name', 'друг'))
                                
                                user_sessions[chat_id] = {
                                    "user_id": user['id'],
                                    "user_name": user.get('first_name', 'Друг'),
                                    "last_question": time.time() - 7200 + 120,
                                    "question_index": 0,
                                    "start_time": time.time()
                                }
                                question_schedule[chat_id] = time.time() + 120
                                
                                print(f"🦐 Новый пользователь: {user.get('first_name')} (ID: {chat_id})")
                            
                            elif text == '/stats':
                                send_stats_message(chat_id, user['id'], user.get('first_name', 'Друг'))
                            
                            elif text == '/help':
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
                        
                        # Обработка нажатий кнопок
                        elif 'callback_query' in update:
                            callback = update['callback_query']
                            user = callback['from']
                            chat_id = callback['message']['chat']['id']
                            callback_data = callback['data']
                            
                            # Сохраняем ответ
                            for question in MINDFULNESS_QUESTIONS:
                                for option in question["options"]:
                                    if option["callback"] == callback_data:
                                        save_response(
                                            user['id'],
                                            user.get('username', user.get('first_name', 'unknown')),
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
            
            # 2. Отправляем вопросы по расписанию
            current_time = time.time()
            
            for chat_id, next_question_time in list(question_schedule.items()):
                if current_time >= next_question_time and chat_id in user_sessions:
                    session = user_sessions[chat_id]
                    
                    question_index = session["question_index"]
                    question = MINDFULNESS_QUESTIONS[question_index % len(MINDFULNESS_QUESTIONS)]
                    
                    if send_mindfulness_question(chat_id, question):
                        print(f"🦐 Вопрос отправлен {session['user_name']}: {question['text'][:30]}...")
                        question_schedule[chat_id] = current_time + 7200
                        user_sessions[chat_id]["question_index"] = question_index + 1
                        user_sessions[chat_id]["last_question"] = current_time
            
            # Короткая пауза
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)

# Запуск только бота (без Flask)
if __name__ == "__main__":
    bot_main_loop()
