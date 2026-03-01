"""
Celery tasks for periodic jobs — Enhanced with Follow-ups and Digest
"""
from celery import Celery
from celery.schedules import crontab
from loguru import logger
import asyncio
from sqlalchemy import select

from config import settings
from scrapers.scraper_manager import run_scraper_task
from database.database import async_session_maker
from database.crud import (
    get_unprocessed_listings, find_matching_subscriptions, 
    mark_listing_processed, get_cars
)
from database.models import User, Car
from utils.notifications import (
    notify_subscribers_about_car, set_bot_instance, 
    send_push_notification
)
from utils.followup import process_pending_followups, send_admin_digest
from utils.lead_scoring import calculate_user_lead_score
from aiogram import Bot

# Configure logging to file
logger.add(
    "logs/celery_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO"
)

# Initialize bot for notifications
bot = Bot(token=settings.bot_token)
set_bot_instance(bot)

# Initialize Celery
celery_app = Celery(
    'avtosavdo_tasks',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
)


@celery_app.task(name='scrape_websites')
def scrape_websites_task():
    """
    Periodic task to scrape OLX and Avtoelon
    Runs every 5 minutes
    """
    try:
        logger.info("Starting website scraping task...")
        
        # Run async scraper in sync context
        loop = asyncio.get_event_loop()
        stats = loop.run_until_complete(run_scraper_task())
        
        logger.info(f"Scraping completed: {stats}")
        
        # Process new listings and notify subscribers
        loop.run_until_complete(process_new_listings())
        
        return stats
    except Exception as e:
        logger.error(f"Error in scraping task: {e}")
        return {'error': str(e)}


async def process_new_listings():
    """Process new scraped listings and notify subscribers"""
    try:
        async with async_session_maker() as session:
            # Get unprocessed listings
            listings = await get_unprocessed_listings(session, limit=100)
            
            if not listings:
                return
            
            logger.info(f"Processing {len(listings)} new listings")
            
            for listing in listings:
                # OLD LOGIC REMOVED: Do not notify users about scraped listings
                # Instead, notify admin if it's a good deal and not yet notified
                
                if listing.is_good_deal and not listing.notified_admin:
                    from utils.notifications import notify_admin_about_good_deal
                    await notify_admin_about_good_deal({
                        'title': listing.title,
                        'brand': listing.brand, 
                        'price': listing.price,
                        'source': listing.source,
                        'url': listing.url
                    })
                    
                    # Update notified flag
                    listing.notified_admin = True
                    # (This will be committed with mark_listing_processed or separate commit if needed)
                
                # Mark as processed
                await mark_listing_processed(session, listing.id)
    
    except Exception as e:
        logger.error(f"Error processing new listings: {e}")


@celery_app.task(name='process_followups')
def process_followups_task():
    """
    Process pending follow-ups
    Runs every 5 minutes
    """
    try:
        logger.info("Processing follow-ups...")
        
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(process_pending_followups(bot))
        
        logger.info(f"Follow-ups processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing follow-ups: {e}")
        return {'error': str(e)}


@celery_app.task(name='send_admin_digest')
def send_admin_digest_task():
    """
    Send admin daily digest
    Runs every day at 9:00 AM
    """
    try:
        logger.info("Sending admin digest...")
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_admin_digest(bot))
        
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Error sending digest: {e}")
        return {'error': str(e)}


@celery_app.task(name='send_weekly_push')
def send_weekly_push_task():
    """
    Send weekly push notifications with top 3 cars
    Runs every Monday at 9:00 AM
    """
    try:
        logger.info("Starting weekly push notification task...")
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_weekly_push())
        
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Error in weekly push task: {e}")
        return {'error': str(e)}


async def send_weekly_push():
    """Send weekly push notifications"""
    try:
        async with async_session_maker() as session:
            # Get top 3 featured cars
            cars = await get_cars(session, is_available=True, limit=3)
            
            if not cars:
                logger.warning("No cars available for weekly push")
                return
            
            # Get all active users
            result = await session.execute(
                select(User).where(User.is_blocked == False)
            )
            users = result.scalars().all()
            
            logger.info(f"Sending weekly push to {len(users)} users")
            
            for user in users:
                await send_push_notification(user.telegram_id, cars)
    
    except Exception as e:
        logger.error(f"Error sending weekly push: {e}")


@celery_app.task(name='recalculate_lead_scores')
def recalculate_lead_scores_task():
    """
    Recalculate all user lead scores
    Runs daily at 3:00 AM
    """
    try:
        logger.info("Recalculating lead scores...")
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(recalculate_all_scores())
        
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Error recalculating scores: {e}")
        return {'error': str(e)}


async def recalculate_all_scores():
    """Recalculate lead scores for all users"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.is_admin == False, User.is_blocked == False)
        )
        users = result.scalars().all()
        
        for user in users:
            await calculate_user_lead_score(session, user.telegram_id)
        
        logger.info(f"Recalculated scores for {len(users)} users")


# Celery Beat schedule
celery_app.conf.beat_schedule = {
    'scrape-every-5-minutes': {
        'task': 'scrape_websites',
        'schedule': 900,  # 900 seconds = 15 minutes
    },
    'process-followups-every-5-minutes': {
        'task': 'process_followups',
        'schedule': 300,  # Every 5 minutes
    },
    'daily-admin-digest': {
        'task': 'send_admin_digest',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
    },
    'weekly-push-notifications': {
        'task': 'send_weekly_push',
        'schedule': crontab(
            day_of_week=settings.weekly_push_day,
            hour=int(settings.weekly_push_time.split(':')[0]),
            minute=int(settings.weekly_push_time.split(':')[1])
        ),
    },
    'recalculate-lead-scores-daily': {
        'task': 'recalculate_lead_scores',
        'schedule': crontab(hour=3, minute=0),  # 3:00 AM daily
    },
}
