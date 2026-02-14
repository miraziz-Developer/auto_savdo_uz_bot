"""
Main bot application — Enhanced with all new handlers
"""
import asyncio
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.database import init_db, close_db
from handlers import (
    common, catalog, subscriptions, admin, favorites, 
    reviews, crm, gallery, sell, analytics,
    buy, price_check, pipeline
)
from utils.notifications import set_bot_instance, notify_admin_about_error


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)


async def on_startup(bot: Bot):
    """Startup actions"""
    logger.info("Bot starting up...")
    set_bot_instance(bot)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Warmup Cache & Currency
    from utils.currency import get_usd_rate
    rate = await get_usd_rate()
    logger.info(f"Currency rates cached: 1 USD = {rate} UZS")
    
    # Run initial scraper check in background (Warmup)
    from scrapers.scraper_manager import run_scraper_task
    asyncio.create_task(run_scraper_task())
    logger.info("Background scraper warmup started")
    
    # Notify admins
    for admin_id in settings.admin_list:
        try:
            await bot.send_message(
                admin_id,
                "🟢 <b>BOT ISHGA TUSHDI! (UNLIMITED MODE)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📊 Barcha tizimlar tayyor:\n"
                "   • 🤖 Bot — ✅\n"
                "   • 🧠 AI Smart Price — ✅\n"
                "   • 💵 Live Currency — ✅\n"
                "   • 📥 Murojaatlar — ✅\n"
                "   • 🛒 Olish arizalari — ✅\n"
                "   • 📋 Pipeline — ✅\n"
                "   • 🔥 Lead Scoring — ✅\n"
                "   • 📞 Auto Follow-up — ✅\n"
                "   • 📊 CRM Dashboard — ✅",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error notifying admin {admin_id}: {e}")
    
    logger.info(f"Admin IDs: {settings.admin_list}")
    
    # Start follow-up scheduler
    asyncio.create_task(start_followup_scheduler(bot))
    logger.info("Follow-up scheduler started")


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


async def start_followup_scheduler(bot: Bot):
    """Run follow-up processing in background (fallback if Celery not available)"""
    from utils.followup import process_pending_followups
    
    while True:
        try:
            await process_pending_followups(bot)
        except Exception as e:
            logger.error(f"Follow-up scheduler error: {e}")
        
        await asyncio.sleep(300)  # Every 5 minutes


async def main():
    """Main function"""
    # Create bot
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Create dispatcher with Redis storage
    try:
        storage = RedisStorage.from_url(settings.redis_url)
        dp = Dispatcher(storage=storage)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Redis not available, using memory storage: {e}")
        dp = Dispatcher()
    
    # Register startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Register all routers (ORDER MATTERS!)
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
    logger.info(f"Registered handlers: common, buy, price_check, pipeline, admin, crm, sell, catalog, subscriptions, favorites, reviews, gallery, analytics")
    
    logger.info(f"Registered handlers: common, buy, price_check, pipeline, admin, crm, sell, catalog, subscriptions, favorites, reviews, gallery, analytics")
    
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
