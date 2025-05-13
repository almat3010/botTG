# Базовый образ с Python
FROM python:3.11-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Создание директории для бота
WORKDIR /app

# Копируем код и зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Запуск бота
CMD ["python", "bot.py"]
