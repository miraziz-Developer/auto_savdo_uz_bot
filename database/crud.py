"""
CRUD operations for database models
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import User, Car, SoldCar, Subscription, Inquiry, ScrapedListing, Favorite, Review


from config import settings

# User CRUD
async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str] = None, 
                             full_name: Optional[str] = None) -> User:
    """Get existing user or create new one"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    # Check if this user should be an admin based on config
    should_be_admin = telegram_id in settings.admin_list
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            is_admin=should_be_admin
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"New user created: {telegram_id} (Admin: {should_be_admin})")
    else:
        # Update last activity (only if > 60 seconds passed) and ensure admin status is synced
        now = datetime.utcnow()
        if not user.last_activity or (now - user.last_activity).total_seconds() > 60:
            user.last_activity = now
            
        if user.is_admin != should_be_admin:
            user.is_admin = should_be_admin
            logger.info(f"User {telegram_id} admin status updated to: {should_be_admin}")
            
        await session.commit()
    
    return user


async def update_user_phone(session: AsyncSession, telegram_id: int, phone: str):
    """Update user phone number"""
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(phone=phone)
    )
    await session.commit()


async def get_all_users(session: AsyncSession) -> List[User]:
    """Get all registered users"""
    result = await session.execute(select(User))
    return result.scalars().all()


async def toggle_user_block(session: AsyncSession, telegram_id: int):
    """Toggle user block status"""
    user = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = user.scalar_one_or_none()
    if user:
        user.is_blocked = not user.is_blocked
        await session.commit()
        return user.is_blocked
    return None


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    """Check if user is admin"""
    # Priority: Settings config
    if telegram_id in settings.admin_list:
        return True
        
    # Fallback: Database
    result = await session.execute(
        select(User.is_admin).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none() or False


# Car CRUD
async def create_car(session: AsyncSession, **kwargs) -> Car:
    """Create new car listing"""
    car = Car(**kwargs)
    session.add(car)
    await session.commit()
    await session.refresh(car)
    logger.info(f"New car created: {car.brand} {car.model} ({car.year})")
    return car


async def get_cars(session: AsyncSession, 
                   brand: Optional[str] = None,
                   model: Optional[str] = None,
                   year_from: Optional[int] = None,
                   year_to: Optional[int] = None,
                   price_from: Optional[float] = None,
                   price_to: Optional[float] = None,
                   transmission: Optional[str] = None,
                   fuel_type: Optional[str] = None,
                   condition: Optional[str] = None,
                   is_available: bool = True,
                   limit: int = 50) -> List[Car]:
    """Get cars with filters"""
    query = select(Car).where(Car.is_available == is_available)
    
    if brand:
        query = query.where(Car.brand.ilike(f"%{brand}%"))
    if model:
        query = query.where(Car.model.ilike(f"%{model}%"))
    if year_from:
        query = query.where(Car.year >= year_from)
    if year_to:
        query = query.where(Car.year <= year_to)
    if price_from:
        query = query.where(Car.price >= price_from)
    if price_to:
        query = query.where(Car.price <= price_to)
    if transmission:
        query = query.where(Car.transmission.ilike(f"%{transmission}%"))
    if fuel_type:
        query = query.where(Car.fuel_type.ilike(f"%{fuel_type}%"))
    if condition:
        query = query.where(Car.condition.ilike(f"%{condition}%"))
    
    query = query.order_by(Car.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_unique_brands(session: AsyncSession) -> List[str]:
    """Get list of unique car brands in stock"""
    result = await session.execute(select(Car.brand).where(Car.is_available == True).distinct())
    return [r for r in result.scalars().all() if r]


async def get_unique_models(session: AsyncSession, brand: str) -> List[str]:
    """Get list of unique models for a brand in stock"""
    result = await session.execute(
        select(Car.model)
        .where(and_(Car.brand == brand, Car.is_available == True))
        .distinct()
    )
    return [r for r in result.scalars().all() if r]


async def get_car_by_id(session: AsyncSession, car_id: int) -> Optional[Car]:
    """Get car by ID"""
    result = await session.execute(select(Car).where(Car.id == car_id))
    return result.scalar_one_or_none()


async def update_car(session: AsyncSession, car_id: int, **kwargs):
    """Update car details"""
    await session.execute(
        update(Car).where(Car.id == car_id).values(**kwargs)
    )
    await session.commit()


async def increment_car_views(session: AsyncSession, car_id: int):
    """Increment car view count"""
    await session.execute(
        update(Car).where(Car.id == car_id).values(views_count=Car.views_count + 1)
    )
    await session.commit()


# Subscription CRUD
async def create_subscription(session: AsyncSession, user_id: int, **criteria) -> Subscription:
    """Create user subscription for car alerts"""
    subscription = Subscription(user_id=user_id, **criteria)
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    logger.info(f"New subscription created for user {user_id}")
    return subscription


async def get_user_subscriptions(session: AsyncSession, user_id: int) -> List[Subscription]:
    """Get all active subscriptions for user"""
    result = await session.execute(
        select(Subscription).where(
            and_(Subscription.user_id == user_id, Subscription.is_active == True)
        )
    )
    return list(result.scalars().all())


async def delete_subscription(session: AsyncSession, subscription_id: int):
    """Delete subscription"""
    await session.execute(
        delete(Subscription).where(Subscription.id == subscription_id)
    )
    await session.commit()


async def find_matching_subscriptions(session: AsyncSession, car: Car) -> List[Subscription]:
    """Find subscriptions matching the car"""
    query = select(Subscription).where(Subscription.is_active == True)
    
    # Build filter conditions
    conditions = []
    
    if car.brand:
        conditions.append(
            or_(
                Subscription.brand.is_(None),
                Subscription.brand.ilike(f"%{car.brand}%")
            )
        )
    
    if car.model:
        conditions.append(
            or_(
                Subscription.model.is_(None),
                Subscription.model.ilike(f"%{car.model}%")
            )
        )
    
    if car.year:
        conditions.append(
            or_(
                Subscription.year_from.is_(None),
                Subscription.year_from <= car.year
            )
        )
        conditions.append(
            or_(
                Subscription.year_to.is_(None),
                Subscription.year_to >= car.year
            )
        )
    
    if car.price:
        conditions.append(
            or_(
                Subscription.price_from.is_(None),
                Subscription.price_from <= car.price
            )
        )
        conditions.append(
            or_(
                Subscription.price_to.is_(None),
                Subscription.price_to >= car.price
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await session.execute(query)
    return list(result.scalars().all())


# Inquiry CRUD
async def create_inquiry(session: AsyncSession, user_id: int, inquiry_type: str, **kwargs) -> Inquiry:
    """Create customer inquiry"""
    inquiry = Inquiry(user_id=user_id, inquiry_type=inquiry_type, **kwargs)
    session.add(inquiry)
    await session.commit()
    await session.refresh(inquiry)
    logger.info(f"New inquiry created: {inquiry_type} from user {user_id}")
    return inquiry


async def get_pending_inquiries(session: AsyncSession) -> List[Inquiry]:
    """Get pending inquiries for admin"""
    result = await session.execute(
        select(Inquiry).where(Inquiry.status == "pending").order_by(Inquiry.created_at.desc())
    )
    return list(result.scalars().all())


async def update_inquiry_status(session: AsyncSession, inquiry_id: int, status: str, admin_notes: Optional[str] = None):
    """Update inquiry status"""
    values = {"status": status, "updated_at": datetime.utcnow()}
    if admin_notes:
        values["admin_notes"] = admin_notes
    
    await session.execute(
        update(Inquiry).where(Inquiry.id == inquiry_id).values(**values)
    )
    await session.commit()


async def get_inquiry_by_id(session: AsyncSession, inquiry_id: int) -> Optional[Inquiry]:
    """Get inquiry by ID"""
    result = await session.execute(select(Inquiry).where(Inquiry.id == inquiry_id))
    return result.scalar_one_or_none()


async def get_user_inquiries(session: AsyncSession, user_id: int) -> List[Inquiry]:
    """Get all inquiries for a specific user"""
    result = await session.execute(
        select(Inquiry).where(Inquiry.user_id == user_id).order_by(Inquiry.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_inquiry(session: AsyncSession, inquiry_id: int):
    """Delete an inquiry"""
    await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
    await session.commit()


# Sold Car CRUD
async def create_sold_car(session: AsyncSession, **kwargs) -> SoldCar:
    """Record sold car"""
    sold_car = SoldCar(**kwargs)
    session.add(sold_car)
    await session.commit()
    await session.refresh(sold_car)
    logger.info(f"Sold car recorded: {sold_car.brand} {sold_car.model}")
    return sold_car


async def get_sold_cars_last_30_days(session: AsyncSession) -> List[SoldCar]:
    """Get sold cars from last 30 days"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await session.execute(
        select(SoldCar).where(SoldCar.sold_at >= thirty_days_ago).order_by(SoldCar.sold_at.desc())
    )
    return list(result.scalars().all())


# Scraped Listing CRUD
async def create_scraped_listing(session: AsyncSession, **kwargs) -> ScrapedListing:
    """Create scraped listing"""
    listing = ScrapedListing(**kwargs)
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


async def get_unprocessed_listings(session: AsyncSession, limit: int = 100) -> List[ScrapedListing]:
    """Get unprocessed scraped listings"""
    result = await session.execute(
        select(ScrapedListing)
        .where(ScrapedListing.is_processed == False)
        .order_by(ScrapedListing.scraped_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_listing_processed(session: AsyncSession, listing_id: int):
    """Mark listing as processed"""
    await session.execute(
        update(ScrapedListing).where(ScrapedListing.id == listing_id).values(is_processed=True)
    )
    await session.commit()


async def listing_exists(session: AsyncSession, external_id: str) -> bool:
    """Check if listing already exists"""
    result = await session.execute(
        select(ScrapedListing.id).where(ScrapedListing.external_id == external_id)
    )
    return result.scalar_one_or_none() is not None


async def get_average_market_price(session: AsyncSession, brand: str, model: str, year: int) -> float:
    """Calculate average market price for a specific car model and year"""
    # Try to get from SoldCars first (real transaction data)
    sold_result = await session.execute(
        select(func.avg(SoldCar.selling_price))
        .where(
            and_(
                func.lower(SoldCar.brand) == brand.lower(),
                func.lower(SoldCar.model) == model.lower(),
                SoldCar.year == year
            )
        )
    )
    sold_avg = sold_result.scalar_one_or_none()
    
    if sold_avg:
        return float(sold_avg)
        
    # Fallback to ScrapedListings (market data)
    scraped_result = await session.execute(
        select(func.avg(ScrapedListing.price))
        .where(
            and_(
                func.lower(ScrapedListing.brand) == brand.lower(),
                func.lower(ScrapedListing.model) == model.lower(),
                ScrapedListing.year == year,
                ScrapedListing.price > 1000  # Filter out unrealistic prices
            )
        )
    )
    scraped_avg = scraped_result.scalar_one_or_none()
    
    return float(scraped_avg) if scraped_avg else 0.0


# Analytics queries
async def get_top_sold_models(session: AsyncSession, limit: int = 10) -> List[dict]:
    """Get top sold car models in last 30 days"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    result = await session.execute(
        select(
            SoldCar.model,
            func.count(SoldCar.id).label('count'),
            func.sum(SoldCar.profit).label('total_profit')
        )
        .where(SoldCar.sold_at >= thirty_days_ago)
        .group_by(SoldCar.model)
        .order_by(func.count(SoldCar.id).desc())
        .limit(limit)
    )
    
    return [
        {"model": row.model, "count": row.count, "total_profit": row.total_profit}
        for row in result.all()
    ]


# Favorite CRUD
async def add_to_favorites(session: AsyncSession, user_id: int, car_id: int) -> bool:
    """Add car to user's favorites"""
    # Check if already in favorites
    result = await session.execute(
        select(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.car_id == car_id)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return False  # Already in favorites
    
    favorite = Favorite(user_id=user_id, car_id=car_id)
    session.add(favorite)
    await session.commit()
    logger.info(f"Car {car_id} added to favorites for user {user_id}")
    return True


async def remove_from_favorites(session: AsyncSession, user_id: int, car_id: int):
    """Remove car from user's favorites"""
    await session.execute(
        delete(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.car_id == car_id)
        )
    )
    await session.commit()
    logger.info(f"Car {car_id} removed from favorites for user {user_id}")


async def get_user_favorites(session: AsyncSession, user_id: int) -> List[Car]:
    """Get user's favorite cars"""
    result = await session.execute(
        select(Car)
        .join(Favorite, Car.id == Favorite.car_id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    return list(result.scalars().all())


async def is_favorite(session: AsyncSession, user_id: int, car_id: int) -> bool:
    """Check if car is in user's favorites"""
    result = await session.execute(
        select(Favorite.id).where(
            and_(Favorite.user_id == user_id, Favorite.car_id == car_id)
        )
    )
    return result.scalar_one_or_none() is not None


# Review CRUD
async def create_review(session: AsyncSession, user_id: int, car_id: int, rating: int, comment: Optional[str] = None):
    """Create car review"""
    # Check if user already reviewed this car
    result = await session.execute(
        select(Review).where(
            and_(Review.user_id == user_id, Review.car_id == car_id)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing review
        existing.rating = rating
        existing.comment = comment
        existing.created_at = datetime.utcnow()
        await session.commit()
        logger.info(f"Review updated for car {car_id} by user {user_id}")
        return existing
    
    # Create new review
    review = Review(user_id=user_id, car_id=car_id, rating=rating, comment=comment)
    session.add(review)
    await session.commit()
    await session.refresh(review)
    logger.info(f"New review created for car {car_id} by user {user_id}")
    return review


async def get_car_reviews(session: AsyncSession, car_id: int) -> List[dict]:
    """Get all reviews for a car with user info"""
    result = await session.execute(
        select(Review, User)
        .join(User, Review.user_id == User.telegram_id)
        .where(Review.car_id == car_id)
        .order_by(Review.created_at.desc())
    )
    
    reviews = []
    for review, user in result.all():
        reviews.append({
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at,
            'user_name': user.full_name or user.username or 'Foydalanuvchi'
        })
    
    return reviews


async def get_car_average_rating(session: AsyncSession, car_id: int) -> float:
    """Get average rating for a car"""
    result = await session.execute(
        select(func.avg(Review.rating))
        .where(Review.car_id == car_id)
    )
    avg_rating = result.scalar_one_or_none()
    return float(avg_rating) if avg_rating else 0.0


async def get_car_review_count(session: AsyncSession, car_id: int) -> int:
    """Get review count for a car"""
    result = await session.execute(
        select(func.count(Review.id))
        .where(Review.car_id == car_id)
    )
    return result.scalar_one_or_none() or 0

