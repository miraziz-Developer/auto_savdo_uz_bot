# 🚀 Avtosavdouz Bot - DEPLOYMENT GUIDE

## 📋 Botni Real Telegramda Ishlatish Uchun QADAMLAR

### 1️⃣ **Bot Token Olish**
```
1. @BotFather ga boring
2. /newcommand deb yozing
3. Bot nomini kiriting (masalan: Avtosavdouz Bot)
4. Username kiriting (masalan: avtosavdouz_bot)
5. Bot tokenini nusxa oling
```

### 2️⃣ **.env Faylini Sozlash**
```bash
# .env.example faylini nusxa oling
cp .env.example .env

# .env faylini oching va quyidagilarni to'ldiring:
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789  # O'zingizning Telegram IDingiz
```

### 3️⃣ **Database Sozlash**

#### **Variant A: Local PostgreSQL**
```bash
# PostgreSQL o'rnatilgan bo'lishi kerak
brew install postgresql  # Mac uchun
sudo apt-get install postgresql  # Linux uchun

# Database yaratish
createdb avtosavdo_bot

# .env faylida sozlang:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=avtosavdo_bot
DB_USER=postgres
DB_PASSWORD=your_password
```

#### **Variant B: Cloud Database (Tavsiya etiladi)**
```bash
# Render.com yoki Railway.app da PostgreSQL yaratish
# DATABASE_URL oling va .env ga qo'shing:
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

### 4️⃣ **Dependencies O'rnatish**
```bash
# Virtual environment yaratish
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# yoki
venv\Scripts\activate  # Windows

# Dependencies o'rnatish
pip install -r requirements.txt

# Playwright brauzerlari o'rnatish
playwright install
```

### 5️⃣ **Botni Ishga Tushirish**
```bash
# Test uchun
python bot.py

# Agar hammasi to'g'ri bo'lsa, bot ishga tushadi va adminlarga xabar yuboradi
```

### 6️⃣ **Production Deploy (Variantlar)**

#### **Variant A: Railway.app**
```bash
1. Railway.com ga kirish
2. New Project -> Deploy from GitHub
3. Repozitoriyani ulash
4. Environment variables qo'shish
5. Deploy qilish
```

#### **Variant B: Render.com**
```bash
1. Render.com ga kirish
2. New -> Web Service
3. GitHub repozitoriyasini ulash
4. Build Command: pip install -r requirements.txt && playwright install
5. Start Command: python bot.py
6. Environment variables qo'shish
```

#### **Variant C: VPS/Server**
```bash
# Serverda:
git clone <repository>
cd avtosavdouz
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install

# Systemd service yaratish
sudo nano /etc/systemd/system/avtosavdouz.service
```

### 7️⃣ **Troubleshooting**

#### **Bot ishlamayapti?**
```bash
# Token to'g'riligini tekshirish:
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Database ulanishini tekshirish:
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())"

# Loglarni ko'rish:
tail -f bot.log
```

#### **Xatoliklar va yechimlari:**
- **409 Conflict**: Bot allaqachon ishlayapti, boshqa instance ni to'xtating
- **Database connection**: .env faylini tekshiring
- **Module not found**: pip install -r requirements.txt qaytadan bajaring

### 8️⃣ **Test Qilish**
```bash
# Bot ishga tushgandan so'ng:
1. Botga /start deb yuboring
2. 🚗 Katalog tugmasini bosing
3. 🤖 AI Tavsiyalar ni sinab ko'ring
4. Admin funksiyalarini tekshiring
```

## 🔧 **Qo'shimcha Sozlamalar**

### **Webhook (Production uchun)**
```python
# bot.py da polling o'rniga webhook qo'shish:
await bot.set_webhook(url="https://yourdomain.com/webhook")
```

### **Monitoring**
```python
# Sentry qo'shish:
SENTRY_DSN=https://your-sentry-dsn
```

## 📞 **Yordam**

Agar muammo yuzaga kelsa:
1. Loglarni tekshiring
2. .env faylini tekshiring  
3. Database ulanishini tekshiring
4. Token to'g'riligini tekshiring

**Bot tayyor! 🎉**
