
import asyncio
import sys
import os
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '.')))

from config import settings
from utils.notifications import publish_scraped_deal, publish_admin_car, set_bot_instance
from aiogram import Bot

async def test_system():
    logger.info("Starting system integration test...")
    
    # Initialize bot for testing
    bot = Bot(token=settings.bot_token)
    set_bot_instance(bot)
    
    # 1. Test Scraped Deal Notification
    test_listing = {
        'brand': 'Chevrolet',
        'model': 'Malibu 2',
        'year': 2021,
        'price': 250000000,
        'location': 'Toshkent',
        'source': 'olx',
        'url': 'https://www.olx.uz/d/obyavlenie/malibu-2-srochno-ID123.html'
    }
    logger.info("Testing: publish_scraped_deal")
    try:
        await publish_scraped_deal(test_listing)
        logger.success("Scraped deal notification test: SUCCESS")
    except Exception as e:
        logger.error(f"Scraped deal notification test: FAILED - {e}")

    # 2. Test Admin Car Notification
    test_car = {
        'brand': 'Hyundai',
        'model': 'Sonata',
        'year': 2023,
        'price': 350000000,
        'color': 'Oq',
        'transmission': 'Avtomat',
        'description': 'Ideal holatda, urilmagan!',
        'images': {'main': 'https://example.com/car.jpg'}
    }
    logger.info("Testing: publish_admin_car")
    try:
        await publish_admin_car(test_car)
        logger.success("Admin car notification test: SUCCESS")
    except Exception as e:
        logger.error(f"Admin car notification test: FAILED - {e}")

    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_system())
