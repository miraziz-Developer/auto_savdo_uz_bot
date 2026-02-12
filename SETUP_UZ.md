# Telegram Bot O'rnatish va Ishga Tushirish Qo'llanmasi

## 1. Tizimni Tayyorlash

### PostgreSQL o'rnatish (macOS)
```bash
brew install postgresql@15
brew services start postgresql@15

# Database yaratish
createdb avtosavdo_bot
```

### Redis o'rnatish
```bash
brew install redis
brew services start redis
```

## 2. Python Environment Sozlash

```bash
# Loyiha papkasiga o'tish
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz

# Virtual environment yaratish
python3 -m venv venv

# Aktivlashtirish
source venv/bin/activate

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Playwright brauzerlarini o'rnatish
playwright install chromium
```

## 3. Konfiguratsiya

1. `.env` fayl yaratish:
```bash
cp .env.example .env
```

2. `.env` faylni tahrirlash:
```bash
nano .env
```

Quyidagi qiymatlarni to'ldiring:
```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # @BotFather dan oling
ADMIN_IDS=123456789,987654321                     # Sizning Telegram ID
DB_PASSWORD=your_password                          # PostgreSQL paroli
TELEGRAM_CHANNEL_ID=@your_channel                  # Kanal username
```

## 4. Botni Ishga Tushirish

### Terminal 1: Bot
```bash
source venv/bin/activate
python bot.py
```

### Terminal 2: Celery Worker
```bash
source venv/bin/activate
celery -A tasks.celery_tasks worker --loglevel=info
```

### Terminal 3: Celery Beat (Scheduler)
```bash
source venv/bin/activate
celery -A tasks.celery_tasks beat --loglevel=info
```

## 5. Test Qilish

### Scraper Test
```bash
python scripts/run_scraper.py
```

Tanlov:
- 1: Faqat OLX
- 2: Faqat Avtoelon
- 3: Hammasi

Natijalar `olx_results.json` va `avtoelon_results.json` fayllariga saqlanadi.

### Analytics Test
```bash
python scripts/generate_analytics.py
```

Grafiklar `analytics/reports/` papkasida saqlanadi.

## 6. Telegram ID ni Topish

Bot bilan `/start` buyrug'ini yuboring, log faylida sizning ID ko'rinadi:
```bash
tail -f logs/bot_*.log
```

Yoki @userinfobot bot orqali ID ni bilib oling.

## 7. Muammolarni Hal Qilish

### PostgreSQL ulanish xatosi
```bash
# PostgreSQL ishlab turganini tekshiring
brew services list | grep postgresql

# Agar to'xtagan bo'lsa
brew services start postgresql@15
```

### Redis ulanish xatosi
```bash
# Redis ishlab turganini tekshiring
redis-cli ping
# Javob: PONG
```

### Playwright xatosi
```bash
# Brauzerlarni qayta o'rnatish
playwright install chromium
```

## 8. Production Deploy

Production serverda ishlatish uchun:

1. **Systemd Service** yarating:
```bash
sudo nano /etc/systemd/system/avtosavdo-bot.service
```

```ini
[Unit]
Description=AvtoSavdo Telegram Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/avtosavdouz
Environment="PATH=/path/to/avtosavdouz/venv/bin"
ExecStart=/path/to/avtosavdouz/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Celery Worker Service**:
```bash
sudo nano /etc/systemd/system/avtosavdo-celery.service
```

3. **Celery Beat Service**:
```bash
sudo nano /etc/systemd/system/avtosavdo-beat.service
```

4. Xizmatlarni ishga tushirish:
```bash
sudo systemctl daemon-reload
sudo systemctl enable avtosavdo-bot
sudo systemctl enable avtosavdo-celery
sudo systemctl enable avtosavdo-beat
sudo systemctl start avtosavdo-bot
sudo systemctl start avtosavdo-celery
sudo systemctl start avtosavdo-beat
```

## 9. Monitoring

### Loglarni ko'rish
```bash
# Bot loglari
tail -f logs/bot_*.log

# Celery loglari
journalctl -u avtosavdo-celery -f
```

### Status tekshirish
```bash
systemctl status avtosavdo-bot
systemctl status avtosavdo-celery
systemctl status avtosavdo-beat
```

## 10. Backup

### Database Backup
```bash
pg_dump -U postgres avtosavdo_bot > backup_$(date +%Y%m%d).sql
```

### Restore
```bash
psql -U postgres avtosavdo_bot < backup_20240210.sql
```

## Yordam

Muammo bo'lsa:
1. Loglarni tekshiring
2. Service statusini ko'ring
3. Database va Redis ishlab turganini tasdiqlang

Omad! 🚀
