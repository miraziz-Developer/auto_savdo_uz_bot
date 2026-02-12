"""
Celery tasks for periodic jobs
"""
from celery import Celery
from celery.schedules import crontab
from loguru import logger
import asyncio

from config import settings
from scrapers.scraper_manager import run_scraper_task

# Configure logging to file
logger.add(
    "logs/celery_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO"
)
from database.database import async_session_maker
from database.crud import get_unprocessed_listings, find_matching_subscriptions, mark_listing_processed
from utils.notifications import notify_subscribers_about_car, set_bot_instance
from aiogram import Bot

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
            
            logger.info(f"Processing {len(listings)} new listings")
            
            for listing in listings:
                # Find matching subscriptions
                # Create a temporary Car-like object for matching
                from database.models import Car
                temp_car = Car(
                    brand=listing.brand,
                    model=listing.model,
                    year=listing.year,
                    price=listing.price
                )
                
                matching_subs = await find_matching_subscriptions(session, temp_car)
                
                if matching_subs:
                    logger.info(f"Found {len(matching_subs)} matching subscriptions for listing {listing.id}")
                    
                    # Notify subscribers
                    for sub in matching_subs:
                        await notify_subscribers_about_car(
                            user_id=sub.user_id,
                            listing_data={
                                'title': listing.title,
                                'brand': listing.brand,
                                'model': listing.model,
                                'year': listing.year,
                                'price': listing.price,
                                'url': listing.url,
                                'source': listing.source
                            }
                        )
                
                # Mark as processed
                await mark_listing_processed(session, listing.id)
    
    except Exception as e:
        logger.error(f"Error processing new listings: {e}")


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
    from database.crud import get_cars
    from utils.notifications import send_push_notification
    from database.models import User
    from sqlalchemy import select
    
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


# Celery Beat schedule
celery_app.conf.beat_schedule = {
    'scrape-every-5-minutes': {
        'task': 'scrape_websites',
        'schedule': settings.scraping_interval,  # 300 seconds = 5 minutes
    },
    'weekly-push-notifications': {
        'task': 'send_weekly_push',
        'schedule': crontab(
            day_of_week=settings.weekly_push_day,
            hour=int(settings.weekly_push_time.split(':')[0]),
            minute=int(settings.weekly_push_time.split(':')[1])
        ),
    },
}
