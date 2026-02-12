#!/bin/bash

# AvtoSavdo Bot - Quick Start Script

echo "🚗 AvtoSavdo Bot - Tez ishga tushirish"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Virtual environment topilmadi. Yaratilmoqda..."
    python3 -m venv venv
    echo "✅ Virtual environment yaratildi"
fi

# Activate virtual environment
echo "🔄 Virtual environment aktivlashtirilmoqda..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/pyvenv.cfg" ]; then
    echo "📥 Kutubxonalar o'rnatilmoqda..."
    pip install -r requirements.txt
    playwright install chromium
    echo "✅ Kutubxonalar o'rnatildi"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env fayli topilmadi!"
    echo "📝 .env.example dan nusxa olinmoqda..."
    cp .env.example .env
    echo ""
    echo "❗ DIQQAT: .env faylini tahrirlang va kerakli ma'lumotlarni kiriting:"
    echo "   - BOT_TOKEN (@BotFather dan)"
    echo "   - ADMIN_IDS (sizning Telegram ID)"
    echo "   - DB_PASSWORD (PostgreSQL paroli)"
    echo ""
    echo "Tahrirlash uchun: nano .env"
    echo ""
    read -p "Davom etishdan oldin .env ni to'ldiring. Tayyormisiz? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Bekor qilindi"
        exit 1
    fi
fi

# Check PostgreSQL
echo "🔍 PostgreSQL tekshirilmoqda..."
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL ishlamayapti!"
    echo "To'xtatildi. Iltimos PostgreSQL ni ishga tushiring:"
    echo "   brew services start postgresql@15"
    exit 1
fi
echo "✅ PostgreSQL ishlayapti"

# Check Redis
echo "🔍 Redis tekshirilmoqda..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis ishlamayapti!"
    echo "To'xtatildi. Iltimos Redis ni ishga tushiring:"
    echo "   brew services start redis"
    exit 1
fi
echo "✅ Redis ishlayapti"

# Create database if not exists
echo "🗄️  Database tekshirilmoqda..."
if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -qw avtosavdo_bot; then
    echo "📝 Database yaratilmoqda..."
    createdb -U postgres avtosavdo_bot
    echo "✅ Database yaratildi"
else
    echo "✅ Database mavjud"
fi

echo ""
echo "✅ Hammasi tayyor!"
echo ""
echo "Botni ishga tushirish uchun quyidagi terminallarni oching:"
echo ""
echo "Terminal 1 (Bot):"
echo "  python bot.py"
echo ""
echo "Terminal 2 (Celery Worker):"
echo "  celery -A tasks.celery_tasks worker --loglevel=info"
echo ""
echo "Terminal 3 (Celery Beat):"
echo "  celery -A tasks.celery_tasks beat --loglevel=info"
echo ""
echo "Yoki barcha servislarni bir vaqtda ishga tushirish uchun:"
echo "  ./start_all.sh"
echo ""
