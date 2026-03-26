#!/usr/bin/env python3
"""
🧪 Bot Test Script - Real Telegramda ishlashini tekshirish
"""
import asyncio
import sys
from aiogram import Bot
from config import settings

async def test_bot_connection():
    """Bot ulanishini test qilish"""
    print("🧪 Bot Test Script")
    print("=" * 50)
    
    try:
        # 1. Token test
        print("1️⃣ Token tekshirilmoqda...")
        bot = Bot(token=settings.bot_token)
        bot_info = await bot.get_me()
        print(f"✅ Bot info: @{bot_info.username} ({bot_info.first_name})")
        
        # 2. Admin IDs test
        print("2️⃣ Admin IDs tekshirilmoqda...")
        if settings.admin_list:
            print(f"✅ Adminlar: {settings.admin_list}")
        else:
            print("⚠️ Adminlar ro'yxati bo'sh!")
        
        # 3. Database test
        print("3️⃣ Database ulanishi tekshirilmoqda...")
        try:
            from database.database import init_db
            await init_db()
            print("✅ Database ulanishi muvaffaqiyatli")
        except Exception as e:
            print(f"❌ Database xatosi: {e}")
            return False
        
        # 4. Handlers test
        print("4️⃣ Handlers tekshirilmoqda...")
        try:
            from handlers.catalog import catalog_handler
            from handlers.admin import admin_dashboard
            print("✅ Handlers muvaffaqiyatli yuklandi")
        except Exception as e:
            print(f"❌ Handlers xatosi: {e}")
            return False
        
        # 5. Test message to admin
        if settings.admin_list:
            print("5️⃣ Test xabar yuborilmoqda...")
            try:
                await bot.send_message(
                    settings.admin_list[0],
                    "🧪 <b>TEST XABAR</b>\n\n"
                    "Bot muvaffaqiyatli ishga tushdi! 🎉\n"
                    "Barcha komponentlar to'g'ri ishlamoqda.",
                    parse_mode="HTML"
                )
                print("✅ Test xabar yuborildi")
            except Exception as e:
                print(f"❌ Xabar yuborish xatosi: {e}")
        
        await bot.session.close()
        
        print("\n" + "=" * 50)
        print("🎉 Barcha testlar muvaffaqiyatli o'tdi!")
        print("📋 Bot real Telegramda ishlaydi!")
        print("\n🚀 Botni ishga tushirish uchun:")
        print("   python bot.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Test xatosi: {e}")
        print("\n🔧 Yechimlar:")
        print("1. .env faylini tekshiring")
        print("2. BOT_TOKEN to'g'ri ekanligiga ishonch hosil qiling")
        print("3. Database ishlayotganiga ishonch hosil qiling")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_bot_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 Test to'xtatildi")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal test error: {e}")
        sys.exit(1)
