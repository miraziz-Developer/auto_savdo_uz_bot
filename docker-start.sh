#!/bin/bash

# AvtoSavdo Bot - Docker Start Script

set -e

echo "🐳 AvtoSavdo Bot - Docker Setup"
echo "================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker ishlamayapti!"
    echo "   Docker Desktop'ni ishga tushiring."
    exit 1
fi

echo "✅ Docker ishlayapti"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 .env faylini yaratish..."
    cp .env.docker .env
    echo "✅ .env yaratildi (.env.docker dan)"
    echo ""
    echo "⚠️  DIQQAT: .env faylini tekshiring!"
    echo "   Kerakli ma'lumotlarni to'ldiring:"
    echo "   - BOT_TOKEN"
    echo "   - ADMIN_IDS"
    echo ""
    read -p "Davom etasizmi? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Bekor qilindi"
        exit 1
    fi
fi

echo "🔨 Docker images yaratilmoqda..."
docker-compose build --no-cache

echo ""
echo "🚀 Servislar ishga tushirilmoqda..."
docker-compose up -d

echo ""
echo "⏳ Servislarning tayyor bo'lishini kutilmoqda..."
sleep 10

echo ""
echo "📊 Servislar holati:"
docker-compose ps

echo ""
echo "✅ Barcha servislar ishga tushdi!"
echo ""
echo "📝 Loglarni ko'rish:"
echo "   docker-compose logs -f bot"
echo ""
echo "🛑 Servislarni to'xtatish:"
echo "   docker-compose down"
echo ""
echo "🔄 Qayta ishga tushirish:"
echo "   docker-compose restart"
echo ""
echo "📊 Servislar holati:"
echo "   docker-compose ps"
echo ""
