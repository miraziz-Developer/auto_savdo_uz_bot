FROM python:3.11-slim

# Buffersiz loglar
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Tizim kutubxonalari
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Talablar fayli oldin ko'chiriladi
COPY requirements.txt .

# Pakletlarni o'rnatish + Playwright
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium


# Loyiha kodlari
COPY . .

# Loglar papkasi
RUN mkdir -p /app/logs /app/analytics/reports

# Bot ishga tushirish
CMD ["python", "bot.py"]

