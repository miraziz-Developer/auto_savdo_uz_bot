"""
Main bot application — Optimized for Free Tier (No Redis, No Celery)
Performance: Minimal logging, optimized pools, graceful shutdown
"""
import asyncio
import signal
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

# Configure logging — WARNING level for production (less disk/CPU usage)
logger.remove()
logger.add(
    sys.stderr,
    format="{time:HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="WARNING"  # Only warnings and errors (was INFO — too verbose)
)
# Separate INFO logger for critical startup messages only
logger.add(
    sys.stderr,
    format="{time:HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    filter=lambda record: record["name"] == "__main__"  # Only main module
)


async def on_startup(bot: Bot):
    """Startup actions"""
    logger.info("Bot starting up...")
    set_bot_instance(bot)
    
    try:
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
                "🟢 <b>BOT ISHGA TUSHDI!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ Optimallashtirilgan rejim\n"
                "🧹 Toza xotira\n"
                "🤖 Scheduler fonida",
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    logger.info(f"Admin IDs: {settings.admin_list}")


async def on_shutdown(bot: Bot):
    """Shutdown actions"""
    logger.info("Bot shutting down...")
    await close_db()
    
    for admin_id in settings.admin_list:
        try:
            await bot.send_message(
                admin_id,
                "🔴 <b>Bot to'xtadi</b>\nQayta ishga tushirilmoqda...",
                parse_mode="HTML"
            )
        except:
            pass


async def main():
    """Main function"""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Memory Storage (RAM efficient, no Redis needed)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    logger.info("Using MemoryStorage for FSM (Lite Mode)")
    
    # Register startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Register all routers
    dp.include_router(common.router)
    dp.include_router(buy.router)
    dp.include_router(price_check.router)
    dp.include_router(pipeline.router)
    dp.include_router(admin.router)
    dp.include_router(crm.router)
    dp.include_router(sell.router)
    dp.include_router(catalog.router)
    dp.include_router(subscriptions.router)
    dp.include_router(favorites.router)
    dp.include_router(reviews.router)
    dp.include_router(gallery.router)
    dp.include_router(analytics.router)
    
    logger.info("All routers registered!")

    # --- BACKGROUND SCHEDULER ---
    scheduler = AsyncIOScheduler()
    
    # Scraper OFF — Free Tier uchun juda og'ir (Browser RAM yeydi)
    # scheduler.add_job(run_scraper_task, 'interval', hours=4)
    
    # Follow-ups (Har 10 daqiqada — was 5 min, too frequent)
    async def periodic_followups():
        try:
            await process_pending_followups(bot)
        except Exception as e:
            logger.error(f"Followup error: {e}")

    scheduler.add_job(periodic_followups, 'interval', minutes=10)
    logger.info("Job added: Follow-ups (every 10m)")
    
    scheduler.start()
    
    # --- GRACEFUL SIGTERM HANDLING ---
    loop = asyncio.get_event_loop()
    
    def handle_sigterm(*args):
        print("Received SIGTERM signal")
        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(graceful_shutdown(dp, bot)))
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Start polling
    try:
        logger.info("Starting bot polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


async def graceful_shutdown(dp: Dispatcher, bot: Bot):
    """Gracefully stop the bot on SIGTERM"""
    try:
        await dp.stop_polling()
        await on_shutdown(bot)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
