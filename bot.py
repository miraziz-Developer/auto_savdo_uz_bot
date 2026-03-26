"""
Main bot application — Optimized v2 (Lite Mode)
Performance: Minimal logging, connection pooling, structured startup
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
    buy, price_check, pipeline, konkurs
)
from utils.notifications import set_bot_instance
from utils.followup import process_pending_followups

# ──────────────────────────────────────────────
# LOGGING SETUP
# ──────────────────────────────────────────────
import logging

class InterceptHandler(logging.Handler):
    """Xususiy loggerdan (aiogram kabi) Loguru'ga o'zgartirish klassi"""
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Basic setup to capture aiogram logs
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

logger.remove()
# Barqaror INFO loglarni ko'rsatish
logger.add(
    sys.stderr,
    format="{time:HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
)

# ──────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────
async def on_startup(bot: Bot):
    """Bot yoqilganda bajariladigan ishlar"""
    logger.info("🚀 Bot starting up...")
    set_bot_instance(bot)

    try:
        db_host = settings.database_url.split('@')[-1] if '@' in settings.database_url else "UNKNOWN"
        logger.info(f"📦 Connecting to DB: {db_host}")
    except Exception:
        pass

    await init_db()
    logger.info("✅ Database ready")

    # Valyuta kursini cache ga olish
    try:
        from utils.currency import get_usd_rate
        rate = await get_usd_rate()
        logger.info(f"💱 USD rate: {rate:,.0f} UZS")
    except Exception as e:
        logger.warning(f"Currency fetch failed (using fallback): {e}")

    # Admin larga xabar
    bot_me = await bot.get_me()
    for admin_id in settings.admin_list:
        try:
            await bot.send_message(
                admin_id,
                f"🟢 <b>BOT ISHGA TUSHDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 @{bot_me.username}\n"
                f"⚡ Lite Mode (MemoryStorage)\n"
                f"🧹 RAM tozalandi",
                parse_mode="HTML"
            )
        except Exception:
            pass

    logger.info(f"📋 Admins: {settings.admin_list}")


# ──────────────────────────────────────────────
# SHUTDOWN
# ──────────────────────────────────────────────
async def on_shutdown(bot: Bot):
    """Bot o'chirilganda bajariladigan ishlar"""
    logger.info("🔴 Bot shutting down...")
    await close_db()

    for admin_id in settings.admin_list:
        try:
            await bot.send_message(
                admin_id,
                "🔴 <b>Bot to'xtadi</b>\nQayta ishga tushirilmoqda...",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
async def main():
    """Asosiy funksiya"""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    logger.info("💾 MemoryStorage (Lite Mode)")

    # Startup / Shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Router'larni tartib bilan ro'yxatga olish ──
    # MUHIM: common.router birinchi o'rinda bo'lishi kerak (/start har qanday holatda ishlashi uchun)
    dp.include_router(common.router)      # Common eng yuqorida!
    dp.include_router(konkurs.router)     # Konkurs button handler
    dp.include_router(admin.router)       # Admin 
    dp.include_router(buy.router)
    dp.include_router(price_check.router)
    dp.include_router(pipeline.router)
    dp.include_router(crm.router)
    dp.include_router(sell.router)
    dp.include_router(catalog.router)
    dp.include_router(subscriptions.router)
    dp.include_router(favorites.router)
    dp.include_router(reviews.router)
    dp.include_router(gallery.router)
    dp.include_router(analytics.router)

    logger.info("✅ All routers registered")

    # ── Background Scheduler ──
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    async def run_followups():
        """Follow-up xabarlarni yuborish — har 10 daqiqada"""
        try:
            result = await process_pending_followups(bot)
            if result.get('processed', 0) > 0:
                logger.info(f"Follow-ups: sent={result['processed']}, failed={result.get('failed', 0)}")
        except Exception as e:
            logger.error(f"Followup error: {e}")

    async def run_scraper():
        """Bozorni skanerlash — har 60 daqiqada"""
        try:
            from scrapers.scraper_manager import run_scraper_task
            stats = await run_scraper_task()
            logger.info(f"Scraper: new={stats.get('new_listings', 0)}, total={stats.get('total', 0)}")
        except Exception as e:
            logger.error(f"Scraper error: {e}")

    async def run_konkurs_leaderboard():
        """Top 10 Liderlar e'loni — har 6 soatda"""
        try:
            from handlers.konkurs import post_konkurs_leaderboard
            await post_konkurs_leaderboard(bot)
            logger.info("Konkurs Leaderboard posted to channel")
        except Exception as e:
            logger.error(f"Konkurs Leaderboard error: {e}")

    scheduler.add_job(run_followups, 'interval', minutes=10, id='followups', misfire_grace_time=60)
    scheduler.add_job(run_scraper, 'interval', minutes=60, id='scraper', misfire_grace_time=300)
    scheduler.add_job(run_konkurs_leaderboard, 'interval', hours=6, id='konkurs', misfire_grace_time=600)
    scheduler.start()
    logger.info("⏰ Scheduler started (follow-ups 10m, scraper 60m, konkurs 6h)")

    # ── SIGTERM xavfsiz o'chirish ──
    loop = asyncio.get_event_loop()

    def handle_sigterm(*args):
        logger.info("📡 SIGTERM received")
        loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(graceful_shutdown(dp, bot, scheduler))
        )

    signal.signal(signal.SIGTERM, handle_sigterm)

    # ── Polling boshlash ──
    MAX_RETRIES = 10
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"📡 Starting polling... (attempt {attempt + 1})")
            await bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(2)  # Short pause before polling to clear old sessions
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                polling_timeout=30,
                handle_signals=False,
            )
            break  # Normal stop — exit loop
        except Exception as e:
            err_str = str(e)
            if "Conflict" in err_str or "409" in err_str:
                wait = 30 + (attempt * 10)
                logger.warning(f"⚡ 409 Conflict detected — another instance? Waiting {wait}s before retry...")
                await asyncio.sleep(wait)
                if attempt >= MAX_RETRIES - 1:
                    logger.critical("💥 Too many 409 conflicts. Check for duplicate bot instances!")
                    break
            else:
                logger.error(f"Polling error: {e}")
                break
    
    scheduler.shutdown(wait=False)
    await bot.session.close()


async def graceful_shutdown(dp: Dispatcher, bot: Bot, scheduler=None):
    """Xavfsiz to'xtatish"""
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        await dp.stop_polling()
        await on_shutdown(bot)
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}")
        sys.exit(1)

