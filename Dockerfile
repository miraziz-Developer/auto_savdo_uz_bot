FROM python:3.9-slim

# Tizim va Redis o'rnatish
RUN apt-get update && apt-get install -y \
    redis-server \
    supervisor \
    libpq-dev \
    gcc \
    curl \
    wait-for-it \
    && rm -rf /var/lib/apt/lists/*

# Playwright brauzerlari uchun kutubxonalar
RUN pip install playwright && playwright install-deps

WORKDIR /app

# Talablar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Kodlarni ko'chirish
COPY . .

# Konfiguratsiya fayli
COPY supervisord.conf /etc/supervisord.conf

# Portni ochish (Render 10000 kutadi)
EXPOSE 10000

# Redis konfiguratsiyasi (bepul rejimda)
RUN sed -i 's/daemonize yes/daemonize no/g' /etc/redis/redis.conf || true

# Supervisord orqali hammasini boshlash
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
