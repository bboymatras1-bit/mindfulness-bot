FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir python-telegram-bot==20.7 python-dotenv==1.0.0
CMD ["python", "mindfulness_bot_v5.py"]
