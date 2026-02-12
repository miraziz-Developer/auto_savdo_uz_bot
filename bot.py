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
    from handlers.common import router as common_router
    from handlers.catalog import router as catalog_router
    from handlers.gallery import router as gallery_router
    from handlers.favorites import router as favorites_router
    from handlers.reviews import router as reviews_router
    from handlers.crm import router as crm_router
    from handlers.admin import router as admin_router
    from handlers.sell import router as sell_router
    from handlers.subscriptions import router as subscriptions_router
    from handlers.analytics import router as analytics_router
    
    dp.include_router(common_router)
    dp.include_router(catalog_router)
    dp.include_router(gallery_router)
    dp.include_router(favorites_router)
    dp.include_router(reviews_router)
    dp.include_router(crm_router)
    dp.include_router(admin_router)
    dp.include_router(sell_router)
    dp.include_router(subscriptions_router)
    dp.include_router(analytics_router)       # NEW
    
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
