# 🚀 Quick Reference - Tezkor Ma'lumotnoma

## 📞 Tizimni Ishga Tushirish

### 1️⃣ Bir Qatorda (Eng Tez):
```bash
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz
./quick_start.sh
```

### 2️⃣ Qo'lda (3 ta terminal):

**Terminal 1 - Bot:**
```bash
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz
source venv/bin/activate
python bot.py
```

**Terminal 2 - Celery Worker:**
```bash
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz
source venv/bin/activate
celery -A tasks.celery_tasks worker --loglevel=info
```

**Terminal 3 - Celery Beat:**
```bash
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz
source venv/bin/activate
celery -A tasks.celery_tasks beat --loglevel=info
```

---

## ⚙️ Muhim Fayllar

| Fayl | Vazifasi | Tahrirlanishi Kerakmi? |
|------|----------|----------------------|
| `.env` | Konfiguratsiya | ✅ **HA** - Bot token, DB password, Admin IDs |
| `bot.py` | Asosiy bot | ❌ YO'Q |
| `config.py` | Sozlamalar | ❌ YO'Q |
| `requirements.txt` | Dependencies | ❌ YO'Q |
| `handlers/*.py` | Bot logic | ⚠️ Agar kerak bo'lsa |
| `database/crud.py` | DB operatsiyalar | ⚠️ Agar kerak bo'lsa |

---

## 🔑 .env Sozlash

```bash
# 1. Nusxa oling
cp .env.example .env

# 2. Tahrirlang
nano .env

# 3. To'ldirish kerak:
BOT_TOKEN=123456:ABC-DEF...          # @BotFather dan
ADMIN_IDS=123456789,987654321         # Sizning Telegram ID
DB_PASSWORD=yourpassword              # PostgreSQL paroli
TELEGRAM_CHANNEL_ID=@your_channel     # Kanal username
```

---

## 🗄️ Database Buyruqlari

### Database Yaratish:
```bash
createdb -U postgres avtosavdo_bot
```

### Database Ko'rish:
```bash
psql -U postgres avtosavdo_bot
```

### SQL Buyruqlar:
```sql
-- Jadvalarni ko'rish
\dt

-- Userlar soni
SELECT COUNT(*) FROM users;

-- Moshinalar soni
SELECT COUNT(*) FROM cars;

-- Sevimlilar soni
SELECT COUNT(*) FROM favorites;

-- Reviews soni
SELECT COUNT(*) FROM reviews;
```

### Database Reset (EHTIYOT!):
```bash
dropdb avtosavdo_bot
createdb avtosavdo_bot
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## 🧪 Test Buyruqlari

### Scraper Test:
```bash
python scripts/run_scraper.py
# 1 - OLX
# 2 - Avtoelon
# 3 - Hammasi
```

### Analytics Test:
```bash
python scripts/generate_analytics.py
```

### Python Shell Test:
```python
python

from database.database import async_session_maker
from database.crud import get_cars
import asyncio

async def test():
    async with async_session_maker() as session:
        cars = await get_cars(session, limit=5)
        print(f"Found {len(cars)} cars")
        for car in cars:
            print(f"- {car.brand} {car.model} ({car.year})")

asyncio.run(test())
```

---

## 📊 Monitoring

### Loglarni Ko'rish:
```bash
# Real-time
tail -f logs/bot_*.log

# Oxirgi 100 qator
tail -n 100 logs/bot_*.log

# Xatolarni topish
grep "ERROR" logs/bot_*.log
```

### Redis Tekshirish:
```bash
redis-cli

# Barcha key'larni ko'rish
KEYS *

# Ma'lum key'ni ko'rish
GET key_name

# Barcha ma'lumotlarni o'chirish (EHTIYOT!)
FLUSHALL
```

### PostgreSQL Tekshirish:
```bash
# Status
brew services list | grep postgresql

# Qayta ishga tushirish
brew services restart postgresql@15

# To'xtatish
brew services stop postgresql@15
```

---

## 🐛 Tez-tez Uchraydigan Muammolar

### 1. Bot ishlamayapti
```bash
# Loglarni tekshiring
tail -f logs/bot_*.log

# Token tekshirish
python -c "from config import settings; print(settings.bot_token)"
```

### 2. Database xatosi
```bash
# PostgreSQL ishlayaptimi?
pg_isready

# Database mavjudmi?
psql -U postgres -lqt | grep avtosavdo_bot
```

### 3. Celery ishlamayapti
```bash
# Redis ishlayaptimi?
redis-cli ping  # Javob: PONG

# Celery worker'ni qayta ishga tushiring
celery -A tasks.celery_tasks worker --loglevel=info
```

### 4. Scraper xatosi
```bash
# Playwright o'rnatish
playwright install chromium

# Test
python scripts/run_scraper.py
```

---

## 📱 Bot Buyruqlari

### Mijoz Buyruqlari:
- `/start` - Boshlash
- `/help` - Yordam
- `🚗 Katalog` - Moshinalarni ko'rish
- `🔍 Qidiruv` - Filtrlar bilan qidirish
- `🔔 Obuna` - Xabar olish uchun
- `❤️ Sevimlilar` - Saqlangan moshinalar
- `📊 Mening obunalarim` - Obunalar ro'yxati

### Admin Buyruqlari:
- `➕ Moshina qo'shish` - Yangi moshina
- `📊 Statistika` - Umumiy ma'lumotlar
- `💰 Sotuvni qayd qilish` - Sold car
- `📥 Murojaatlar` - Customer inquiries
- `📊 CRM Dashboard` - Batafsil analytics
- `🔍 Parsing Dashboard` - Scraping results

---

## 🔢 Versiya Ma'lumotlari

**Versiya:** 2.0  
**Sana:** 2026-02-10  
**Python:** 3.9+  
**Aiogram:** 3.4.1  
**PostgreSQL:** 15+  
**Redis:** 7+  

---

## 📚 Qo'shimcha Hujjatlar

| Hujjat | Tavsif |
|--------|--------|
| `README_UZ.md` | To'liq O'zbekcha qo'llanma |
| `SETUP_UZ.md` | O'rnatish yo'riqnomasi |
| `SYSTEM_GUIDE_UZ.md` | Tizim qanday ishlaydi |
| `ARCHITECTURE_DIAGRAM.md` | Arxitektura diagrammalari |
| `CHANGELOG.md` | O'zgarishlar tarixi |

---

## 🆘 Yordam

### Savol bo'lsa:
1. Loglarni tekshiring: `tail -f logs/bot_*.log`
2. Database'ni tekshiring: `psql -U postgres avtosavdo_bot`
3. Redis'ni tekshiring: `redis-cli ping`
4. Hujjatlarni o'qing

### Tizimni to'xtatish:
```bash
# Bot (Ctrl+C)
# Celery Worker (Ctrl+C)
# Celery Beat (Ctrl+C)

# Yoki barcha Python jarayonlarni to'xtatish (EHTIYOT!)
# pkill -f python
```

---

## ✅ Checklist

Ishga tushirishdan oldin tekshiring:

- [ ] PostgreSQL ishlamoqda (`brew services list`)
- [ ] Redis ishlamoqda (`redis-cli ping`)
- [ ] `.env` fayli to'ldirilgan
- [ ] Bot token to'g'ri (`@BotFather`)
- [ ] Admin ID to'g'ri (`@userinfobot`)
- [ ] Database yaratilgan (`psql -l | grep avtosavdo`)
- [ ] Virtual env faollashtirilgan (`source venv/bin/activate`)
- [ ] Dependencies o'rnatilgan (`pip list`)

---

**Omad tilaymiz! 🚀**
