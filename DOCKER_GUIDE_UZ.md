# 🐳 Docker - Qo'llanma

## 📖 Docker nima?

Docker - bu ilovalarni container'larda ishga tushirish platformasi. Container - bu ilovangiz va uning barcha dependenc ies'lari birgalikda ishlaydigan izolyatsiya qilingan muhit.

### Afzalliklar:
- ✅ **Portability** - Bir joyda ishlasa, hamma joyda ishlaydi
- ✅ **Isolation** - Har bir servis o'z container'ida
- ✅ **Consistency** - Development = Production
- ✅ **Easy scaling** - Oson kengaytirish

---

## 🚀 Tezkor Start

### 1️⃣ Docker Desktop'ni Ishga Tushirish

```bash
# macOS
open -a Docker

# 20-30 soniya kuting Docker tayyor bo'lishini
```

### 2️⃣ Bir Buyruqda Hamma Narsani Ishga Tushirish

```bash
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz
./docker-start.sh
```

**Yoki qo'lda:**

```bash
# .env faylini yaratish  
cp .env.docker .env

# Build qilish
docker-compose build

# Ishga tushirish
docker-compose up -d
```

---

## 📊 Docker Compose Servislari

Bizning `docker-compose.yml` faylida **5 ta servis** bor:

### 1. **postgres** 🗄️
- PostgreSQL 15 database
- Port: 5432
- Volume: `postgres_data` (ma'lumotlar saqlanadi)

### 2. **redis** 🔴
- Redis 7 cache/FSM storage
- Port: 6379
- Volume: `redis_data`

### 3. **bot** 🤖
- Telegram bot (asosiy)
- `.env` faylidan konfiguratsiya
- Logs: `./logs` papkaga yoziladi

### 4. **celery_worker** ⚙️
- Background tasks (scraping, notifications)
- Redis'ga ulanadi

### 5. **celery_beat** ⏰
- Scheduler (har 5 minut, har hafta)
- Redis'ga ulanadi

---

## 🎯 Asosiy Buyruqlar

### Servislarni Ishga Tushirish:
```bash
docker-compose up -d
```
- `-d` = detached mode (background'da)

### Servislarni Ko'rish:
```bash
docker-compose ps
```

### Loglarni Ko'rish:
```bash
# Barcha servislar
docker-compose logs -f

# Faqat bot
docker-compose logs -f bot

# Faqat celery worker
docker-compose logs -f celery_worker

# Oxirgi 100 qator
docker-compose logs --tail=100 bot
```

### Servislarni To'xtatish:
```bash
# To'xtatish (container'lar saqlanadi)
docker-compose stop

# To'xtatish va o'chirish
docker-compose down

# To'xtatish, o'chirish va volume'larni ham o'chirish
docker-compose down -v
```

### Qayta Ishga Tushirish:
```bash
# Barcha servislar
docker-compose restart

# Faqat bot
docker-compose restart bot
```

### Rebuild (Kod o'zgarganda):
```bash
# Build qayta qilish
docker-compose build

# Build + restart
docker-compose up -d --build
```

---

## 🔧 Debugging

### Container'ga Kirish:
```bash
# Bot container'ga kirish
docker-compose exec bot bash

# PostgreSQL'ga kirish
docker-compose exec postgres psql -U postgres avtosavdo_bot

# Redis CLI
docker-compose exec redis redis-cli
```

### Database Tekshirish:
```bash
docker-compose exec postgres psql -U postgres avtosavdo_bot -c "SELECT COUNT(*) FROM users;"
```

### Container Statusini Tekshirish:
```bash
# Barcha container'larni ko'rish
docker ps

# To'xatgan container'lar ham
docker ps -a
```

### Resources (CPU, Memory):
```bash
docker stats
```

---

## 📁 Volume'lar (Ma'lumotlar)

Volume'lar - bu container'lardan tashqarida saqlanadigan ma'lumotlar.

### Bizning volume'larimiz:
```bash
# Ro'yxat
docker volume ls

# postgres_data - PostgreSQL ma'lumotlari
# redis_data - Redis ma'lumotlari
```

### Volume'larni boshqarish:
```bash
# Volume haqida ma'lumot
docker volume inspect avtosavdouz_postgres_data

# Volume'ni o'chirish (EHTIYOT!)
docker volume rm avtosavdouz_postgres_data

# Barcha ishlatilmayotgan volume'larni o'chirish
docker volume prune
```

---

## 🌐 Network

Container'lar `avtosavdo_network` networkida birlashgan.

```bash
# Network haqida ma'lumot
docker network inspect avtosavdouz_avtosavdo_network

# Container'lar bir-biriga hostname orqali murojaat qiladi:
# - bot → postgres:5432
# - bot → redis:6379
```

---

## 🐛 Troubleshooting

### Problem 1: Docker ishlamayapti
```bash
# Docker Desktop'ni ochish
open -a Docker

# Statusni tekshirish
docker info
```

### Problem 2: Port band
```bash
# Port'ni ishlatayotgan jarayonni topish
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Local PostgreSQL/Redis'ni to'xtatish
brew services stop postgresql
brew services stop redis
```

### Problem 3: Build xatosi
```bash
# Cache'siz build
docker-compose build --no-cache

# Container'larni tozalash
docker system prune -a
```

### Problem 4: Volume ma'lumotlarini reset
```bash
# To'xtatish va volume'larni o'chirish
docker-compose down -v

# Qayta ishga tushirish
docker-compose up -d
```

### Problem 5: Bot ishlamayapti
```bash
# Loglarni tekshirish
docker-compose logs bot

# Container'ga kirish va test
docker-compose exec bot python -c "from config import settings; print(settings.bot_token)"
```

---

## 🔄 Update Qilish (Kod O'zgarganda)

```bash
# 1. Container'larni to'xtatish
docker-compose down

# 2. Kodni pull/update qilish
git pull  # Agar git'dan

# 3. Rebuild va restart
docker-compose build
docker-compose up -d

# Yoki bir qatorda:
docker-compose up -d --build
```

---

## 📊 Production Deployment

### Optimized Build:
```bash
# Production uchun build
docker-compose -f docker-compose.yml build

# Background'da ishga tushirish
docker-compose up -d
```

### Monitoring:
```bash
# Real-time logs
docker-compose logs -f --tail=100

# Stats
docker stats

# Health check
docker-compose ps
```

### Backup:
```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U postgres avtosavdo_bot > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20260210.sql | docker-compose exec -T postgres psql -U postgres avtosavdo_bot
```

---

## 🎯 Docker vs Local

| Feature | Local | Docker |
|---------|-------|--------|
| Setup | Qiyin (PostgreSQL, Redis install) | Oson (1 buyruq) |
| Portability | Yo'q (OS specific) | Ha (hamma joyda) |
| Isolation | Yo'q | Ha |
| Cleanup | Qo'lda | `docker-compose down` |
| Scaling | Qiyin | Oson |

---

## 📝 .env Konfiguratsiya

Docker uchun `.env` faylida:

```bash
# Local host emas, Docker service nomlari
DB_HOST=postgres      # localhost emas!
REDIS_HOST=redis      # localhost emas!

# Celery broker
CELERY_BROKER_URL=redis://redis:6379/1
```

---

## ✅ Checklist

Ishga tushirishdan oldin:

- [ ] Docker Desktop o'rnatilgan va ishga tushgan
- [ ] `.env` fayli to'ldirilgan
- [ ] Local PostgreSQL/Redis to'xtatilgan (port conflict)
- [ ] `docker-compose.yml` tekshirilgan
- [ ] `docker-compose build` xatosiz bajarildi

---

## 🚀 Quick Commands Cheat Sheet

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# View logs
docker-compose logs -f bot

# Check status
docker-compose ps

# Enter container
docker-compose exec bot bash

# Database access
docker-compose exec postgres psql -U postgres avtosavdo_bot

# Restart specific service
docker-compose restart bot

# Remove everything (including volumes)
docker-compose down -v
```

---

**Omad tilaymiz Docker bilan! 🐳🚀**
