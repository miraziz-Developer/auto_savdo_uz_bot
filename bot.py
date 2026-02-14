"""
Main bot application — Optimized for Free Tier (No Redis, No Celery)
"""
import asyncio
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database.database import init_db, close_db
from handlers import (
    common, catalog, subscriptions, admin, favorites, 
    reviews, crm, gallery, sell, analytics,
    buy, price_check, pipeline
)
from utils.notifications import set_bot_instance
from utils.followup import process_pending_followups
from scrapers.scraper_manager import run_scraper_task

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


async def on_startup(bot: Bot):
    """Startup actions"""
    logger.info("Bot starting up...")
    set_bot_instance(bot)
    
    # Initialize database
    try:
        # Hide password for security log
        safe_url = settings.database_url.split('@')[-1] if '@' in settings.database_url else "UNKNOWN"
        logger.info(f"Connecting to DB Host: {safe_url}")
    except: pass

    await init_db()
    logger.info("Database initialized")
    
    # Warmup Cache & Currency
    try:
        from utils.currency import get_usd_rate
        rate = await get_usd_rate()
        logger.info(f"Currency rates cached: 1 USD = {rate} UZS")
    except Exception as e:
        logger.error(f"Error fetching currency: {e}")
    
    # Notify admins
    for admin_id in settings.admin_list:
        try:
            await bot.send_message(
                admin_id,
                "🟢 <b>BOT ISHGA TUSHDI! (LITE MODE)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ RAM Optimallashtirildi\n"
                "🧹 Toza xotira rejimi\n"
                "🤖 Scheduler fonida ishlaydi",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error notifying admin {admin_id}: {e}")
    
    logger.info(f"Admin IDs: {settings.admin_list}")


async def on_shutdown(bot: Bot):
    """Shutdown actions"""
    logger.info("Bot shutting down...")
    await close_db()
    
    for admin_id in settings.admin_list:
        try:
            await bot.send_message(
                admin_id,
                "🔴 <b>Bot to'xtadi</b>\n"
                "Qayta ishga tushirilmoqda...",
                parse_mode="HTML"
            )
        except:
            pass


async def main():
    """Main function"""
    # Create bot
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Create dispatcher with Memory Storage (RAM efficient)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    logger.info("Using MemoryStorage for FSM (Lite Mode)")
    
    # Register startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Register all routers
    dp.include_router(common.router)       # /start, /help
    dp.include_router(buy.router)          # 🛒 Moshina olish
    dp.include_router(price_check.router)  # 📊 Narxni baholash
    dp.include_router(pipeline.router)     # 📋 Pipeline (Admin)
    dp.include_router(admin.router)        # Admin commands
    dp.include_router(crm.router)          # CRM Dashboard
    dp.include_router(sell.router)         # ➕ E'lon berish
    dp.include_router(catalog.router)      # 🔍 Qidiruv
    dp.include_router(subscriptions.router) # 🔔 Obunalar
    dp.include_router(favorites.router)    # ❤️ Sevimlilar
    dp.include_router(reviews.router)      # ⭐ Sharhlar
    dp.include_router(gallery.router)      # 🖼 Galereya
    dp.include_router(analytics.router)    # 📊 Statistika
    
    logger.info("All routers registered!")

    # --- BACKGROUND SCHEDULER (Lite Version) ---
    scheduler = AsyncIOScheduler()
    
    # 1. Scraper (Har 4 soatda)
    scheduler.add_job(run_scraper_task, 'interval', hours=4)
    logger.info("Job added: Scraper (every 4h)")
    
    # 2. Follow-ups (Har 5 daqiqada)
    async def periodic_followups():
        await process_pending_followups(bot)
    scheduler.add_job(periodic_followups, 'interval', minutes=5)
    logger.info("Job added: Follow-ups (every 5m)")
    
    # Start Scheduler
    scheduler.start()
    
    # Start polling
    try:
        logger.info("Starting bot polling...")
        # Drop pending updates
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
