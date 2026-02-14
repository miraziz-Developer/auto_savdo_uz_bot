#!/bin/bash

# Ranglar
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AVTOSAVDO BOT DEPLOYMENT BOSHLANDI...${NC}"

# 1. Kodni yangilash
echo -e "${GREEN}📥 Kodlar yangilanmoqda (git pull)...${NC}"
git pull origin main
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Git pull xatolik berdi! Iltimos, tekshiring.${NC}"
    exit 1
fi

# 2. Eskisini to'xtatish
echo -e "${BLUE}🛑 Eski konteynerlar to'xtatilmoqda...${NC}"
docker-compose down

# 3. Cache va keraksiz fayllarni tozalash (ixtiyoriy, joyni tejash uchun)
echo -e "${BLUE}🧹 Tizim tozalanmoqda...${NC}"
# docker system prune -f  # Ehtiyotkorlik uchun kommentda qoldirdim

# 4. Yangi versiyani qurish va ishga tushirish
echo -e "${GREEN}🏗️ Yangi versiya qurilmoqda va ishga tushirilmoqda...${NC}"
docker-compose up --build -d

# 5. Status tekshirish
echo -e "${GREEN}✅ Tizim muvaffaqiyatli ishga tushdi!${NC}"
echo -e "${BLUE}📜 Loglarni ko'rsataman (Chiqish uchun Ctrl+C bosing):${NC}"
echo "---------------------------------------------------"
docker-compose logs -f --tail=50
