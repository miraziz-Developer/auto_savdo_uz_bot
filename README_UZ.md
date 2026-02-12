# 🚗 AvtoSavdo Bot - To'liq Loyiha

## 📊 Loyiha Tavsifi

Professional Telegram bot moshina savdosi biznesi uchun. OLX.uz va Avtoelon.uz saytlaridan avtomatik parsing, mijozlar uchun obuna tizimi, admin panel va to'liq analitika.

## ✨ Asosiy Funksiyalar

### 👥 Mijozlar uchun
- 🚗 Katalog (filtrlash bilan)
- 🔍 Qidiruv
- 🔔 Obuna (yangi moshinalar haqida xabar)
- 💰 Moshina sotish (admin ga murojaat)

### 🔑 Admin panel
- ➕ Moshina qo'shish
- 📊 Statistika va grafiklar
- 💰 Sotuvlarni qayd qilish
- 📥 Murojaatlarni ko'rish
- 🔍 Parsing Dashboard
- 📢 Xabar yuborish (broadcast)

### 🤖 Backend
- 🕷️ Har 5 minutda OLX va Avtoelon parsing
- 🔔 Avtomatik xabarnomalar
- 📊 Pandas + Matplotlib analitika
- 📤 Telegram kanal va Instagram e'lon
- ⏰ Celery task scheduler

## 📁 Loyiha Strukturasi

```
avtosavdouz/
├── 📄 bot.py                    # Asosiy bot
├── ⚙️ config.py                 # Konfiguratsiya
├── 📋 requirements.txt          # Dependencies
├── 📖 README.md                 # Inglizcha qo'llanma
├── 📖 SETUP_UZ.md              # O'zbekcha o'rnatish
├── 🚀 quick_start.sh           # Tez ishga tushirish
│
├── 🗄️ database/
│   ├── models.py               # SQLAlchemy modellari
│   ├── database.py             # DB ulanish
│   └── crud.py                 # CRUD operatsiyalar
│
├── 🎮 handlers/
│   ├── common.py               # /start, /help
│   ├── catalog.py              # Katalog va qidiruv
│   ├── subscriptions.py        # Obuna tizimi
│   └── admin.py                # Admin panel
│
├── ⌨️ keyboards/
│   ├── user_keyboards.py       # Foydalanuvchi klaviaturalari
│   └── admin_keyboards.py      # Admin klaviaturalari
│
├── 📝 states/
│   └── states.py               # FSM state'lar
│
├── 🕷️ scrapers/
│   ├── base_scraper.py         # Asosiy scraper class
│   ├── olx_scraper.py          # OLX.uz scraper
│   ├── avtoelon_scraper.py     # Avtoelon.uz scraper
│   └── scraper_manager.py      # Koordinator
│
├── 📊 analytics/
│   └── sales_analytics.py      # Sotuvlar analitikasi
│
├── ⏰ tasks/
│   └── celery_tasks.py         # Periodic tasks
│
├── 🔧 utils/
│   ├── notifications.py        # Xabarnomalar
│   └── formatters.py           # Text formatlash
│
└── 📜 scripts/
    ├── run_scraper.py          # Scraper test
    └── generate_analytics.py   # Analytics test
```

## 🛠️ Texnologiyalar

- **Bot**: Aiogram 3.x
- **Database**: PostgreSQL + SQLAlchemy (async)
- **Cache/FSM**: Redis
- **Scraping**: Playwright + BeautifulSoup
- **Tasks**: Celery + Redis
- **Analytics**: pandas + matplotlib
- **Logs**: loguru

## 📊 Ma'lumotlar Bazasi Strukturasi

### Users (Foydalanuvchilar)
- telegram_id (unique)
- username, full_name
- phone, is_admin, is_blocked
- created_at, last_activity

### Cars (Moshinalar)
- brand, model, year, price
- mileage, color, condition
- transmission, fuel_type
- description, images
- is_available, is_featured
- views_count, expert_notes
- source, source_url

### Subscriptions (Obunalar)
- user_id
- brand, model
- year_from, year_to
- price_from, price_to
- condition, is_active

### SoldCars (Sotilgan moshinalar)
- brand, model, year
- purchase_price, selling_price
- profit, sold_at
- buyer_id, notes

### ScrapedListings (Parse qilingan e'lonlar)
- source (olx, avtoelon)
- external_id, url
- title, brand, model, year, price
- images, is_processed, is_good_deal

## 🚀 O'rnatish va Ishga Tushirish

### Tez usul:
```bash
./quick_start.sh
```

### Qo'lda usul:

1. **Dependencies o'rnatish:**
```bash
# PostgreSQL
brew install postgresql@15
brew services start postgresql@15

# Redis
brew install redis
brew services start redis

# Python packages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

2. **Konfiguratsiya:**
```bash
cp .env.example .env
nano .env  # .env ni to'ldiring
```

3. **Database yaratish:**
```bash
createdb avtosavdo_bot
```

4. **Bot ishga tushirish:**
```bash
# Terminal 1
python bot.py

# Terminal 2
celery -A tasks.celery_tasks worker --loglevel=info

# Terminal 3
celery -A tasks.celery_tasks beat --loglevel=info
```

## 📝 Muhim Ma'lumotlar

### BOT_TOKEN olish
1. Telegram'da @BotFather ga boring
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username'ni kiriting
4. Token'ni nusxalang

### Telegram ID topish
1. @userinfobot ga `/start` yuboring
2. Yoki bot loglaridan toping:
```bash
tail -f logs/bot_*.log
```

### Kanal ID topish
1. Kanal yarating (public)
2. Username bering (@your_channel)
3. `.env` ga qo'shing

## 📊 Scraper Test

```bash
python scripts/run_scraper.py
```

Tanlov:
- 1: Faqat OLX
- 2: Faqat Avtoelon
- 3: Hammasi

Natija: `olx_results.json`, `avtoelon_results.json`

## 📈 Analytics Test

```bash
python scripts/generate_analytics.py
```

Grafiklar: `analytics/reports/*.png`

## 🔧 Muammolarni Hal Qilish

### PostgreSQL xatosi:
```bash
brew services restart postgresql@15
```

### Redis xatosi:
```bash
brew services restart redis
redis-cli ping  # Javob: PONG
```

### Playwright xatosi:
```bash
playwright install chromium
```

### Database reset (EHTIYOT: Barcha ma'lumot o'chadi):
```bash
dropdb avtosavdo_bot
createdb avtosavdo_bot
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())"
```

## 📊 Monitoring

### Loglar:
```bash
tail -f logs/bot_*.log
```

### Database:
```bash
psql -U postgres avtosavdo_bot
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM cars;
```

### Redis:
```bash
redis-cli
KEYS *
```

## 🎯 Keyingi Qadamlar

- [ ] Instagram API integratsiya
- [ ] To'lov tizimi
- [ ] Sevimlilar funksiyasi
- [ ] Rasmlar galereyasi
- [ ] Advanced filtrlar
- [ ] Foydalanuvchi sharhlar
- [ ] CRM dashboard

## 📞 Yordam

Muammolar yoki savollar bo'lsa:
- Loglarni tekshiring
- Database va Redis statusini ko'ring
- GitHub Issues yaratish (agar ochiq repo bo'lsa)

## 📜 Litsenziya

Private project - Barcha huquqlar himoyalangan

---

**Omad tilaklar! 🚀 Biznesingiz gullab-yashnsin!**
