"""
Main bot application
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
from handlers import common, catalog, subscriptions, admin, favorites, reviews, crm, gallery, sell
from utils.notifications import set_bot_instance, notify_admin_about_error


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Custom sink for Telegram error notifications
def telegram_error_sink(message):
    record = message.record
    if record["level"].name in ["ERROR", "CRITICAL"]:
        # Use run_coroutine_threadsafe or create a task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(notify_admin_about_error(record["message"]))
        except Exception as e:
            print(f"Error in telegram_error_sink: {e}", file=sys.stderr)

logger.add(telegram_error_sink, level="ERROR")

logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


async def main():
    """Main bot function"""
    logger.info("Starting AvtoSavdo Bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize bot
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Set bot instance for notifications
    set_bot_instance(bot)
    
    # Initialize Redis storage for FSM
    storage = RedisStorage.from_url(settings.redis_url)
    
    # Initialize dispatcher
    dp = Dispatcher(storage=storage)
    
    # Register middleware
    from utils.middleware import BlockCheckMiddleware
    dp.update.middleware(BlockCheckMiddleware())
    
    # Register routers
    dp.include_router(common.router)
    dp.include_router(catalog.router)
    dp.include_router(subscriptions.router)
    dp.include_router(favorites.router)  # NEW
    dp.include_router(reviews.router)    # NEW
    dp.include_router(gallery.router)    # NEW
    dp.include_router(admin.router)
    dp.include_router(crm.router)        # NEW
    dp.include_router(sell.router)       # NEW
    
    logger.info("Handlers registered")
    
    # Start bot
    try:
        logger.info("Bot is running...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    finally:
        await bot.session.close()
        await close_db()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
