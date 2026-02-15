"""
CRUD operations for database models — Enhanced with Lead Scoring, Follow-ups, Pipeline
"""
from typing import Optional, List
import re
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import (
    User, Car, SoldCar, Subscription, Inquiry, ScrapedListing,
    Favorite, Review, BuyRequest, FollowUp, ContactLog
)

from config import settings

# ====== USER CRUD ======

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str] = None, 
                             full_name: Optional[str] = None) -> User:
    """Get existing user or create new one"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    should_be_admin = telegram_id in settings.admin_list
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            is_admin=should_be_admin,
            source="telegram"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"New user created: {telegram_id} (Admin: {should_be_admin})")
    else:
        now = datetime.utcnow()
        if not user.last_activity or (now - user.last_activity).total_seconds() > 60:
            user.last_activity = now
            
        if user.is_admin != should_be_admin:
            user.is_admin = should_be_admin
            logger.info(f"User {telegram_id} admin status updated to: {should_be_admin}")
            
        if username and user.username != username:
            user.username = username
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            
        await session.commit()
    
    return user


async def get_user_by_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Get user by telegram ID"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def update_user_phone(session: AsyncSession, telegram_id: int, phone: str):
    """Update user phone number"""
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(phone=phone)
    )
    await session.commit()


async def update_user_lead_data(session: AsyncSession, telegram_id: int, **kwargs):
    """Update user lead scoring data"""
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(**kwargs)
    )
    await session.commit()


async def increment_user_views(session: AsyncSession, telegram_id: int):
    """Increment user total views"""
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(
            total_views=User.total_views + 1
        )
    )
    await session.commit()


async def get_all_users(session: AsyncSession) -> List[User]:
    """Get all registered users"""
    result = await session.execute(select(User).where(User.is_blocked == False))
    return result.scalars().all()


async def get_hot_leads(session: AsyncSession, min_score: int = 60, limit: int = 20) -> List[User]:
    """Get hot leads — yuqori ball olgan mijozlar"""
    result = await session.execute(
        select(User)
        .where(
            User.is_blocked == False,
            User.is_admin == False,
            User.lead_score >= min_score
        )
        .order_by(User.lead_score.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def toggle_user_block(session: AsyncSession, telegram_id: int):
    """Toggle user block status"""
    user = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = user.scalar_one_or_none()
    if user:
        user.is_blocked = not user.is_blocked
        await session.commit()
        return user.is_blocked
    return None


async def update_user_conversion(session: AsyncSession, telegram_id: int, status: str, notes: Optional[str] = None):
    """Update user conversion status"""
    values = {"conversion_status": status}
    if notes:
        values["admin_notes"] = notes
    values["last_contacted_at"] = datetime.utcnow()
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(**values)
    )
    await session.commit()


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    """Check if user is admin"""
    if telegram_id in settings.admin_list:
        return True
    result = await session.execute(
        select(User.is_admin).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none() or False


# ====== CAR CRUD ======

async def create_car(session: AsyncSession, **kwargs) -> Car:
    """Create new car listing"""
    car = Car(**kwargs)
    session.add(car)
    await session.commit()
    await session.refresh(car)
    logger.info(f"New car created: {car.brand} {car.model} ({car.year})")

async def find_interested_users(session: AsyncSession, brand: str, model: str, year: int, price: float) -> List[int]:
    """Find users interested in these parameters (Subscriptions & Buy Requests)"""
    from sqlalchemy import or_

    if not brand or not model:
        return []

    # 1. Matching Subscriptions
    sub_query = select(Subscription.user_id).where(
        Subscription.is_active == True,
        # Brand match
        or_(Subscription.brand == None, Subscription.brand == "", func.lower(Subscription.brand) == brand.lower()),
        # Model match
        or_(Subscription.model == None, Subscription.model == "", func.lower(Subscription.model) == model.lower()),
        # Year range
        or_(Subscription.year_from == None, Subscription.year_from <= year),
        or_(Subscription.year_to == None, Subscription.year_to >= year),
        # Price range
        or_(Subscription.price_from == None, Subscription.price_from <= price),
        or_(Subscription.price_to == None, Subscription.price_to >= price)
    )
    
    # 2. Matching Buy Requests
    req_query = select(BuyRequest.user_id).where(
        BuyRequest.status.in_(['pending', 'searching', 'found_options']),
        or_(BuyRequest.brand == None, BuyRequest.brand == "", func.lower(BuyRequest.brand) == brand.lower()),
        or_(BuyRequest.model == None, BuyRequest.model == "", func.lower(BuyRequest.model) == model.lower()),
        or_(BuyRequest.year_from == None, BuyRequest.year_from <= year),
        or_(BuyRequest.year_to == None, BuyRequest.year_to >= year),
        or_(BuyRequest.budget_min == None, BuyRequest.budget_min * 0.9 <= price),
        or_(BuyRequest.budget_max == None, BuyRequest.budget_max * 1.1 >= price)
    )
    
    subs = await session.execute(sub_query)
    reqs = await session.execute(req_query)
    
    return list(set(subs.scalars().all()) | set(reqs.scalars().all()))


async def get_matching_users_for_car(session: AsyncSession, car: Car) -> List[int]:
    """Wrapper for car object"""
    return await find_interested_users(session, car.brand, car.model, car.year, car.price)


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


async def update_car_pipeline(session: AsyncSession, car_id: int, status: str):
    """Update car pipeline status"""
    await session.execute(
        update(Car).where(Car.id == car_id).values(
            pipeline_status=status,
            pipeline_updated_at=datetime.utcnow()
        )
    )
    await session.commit()


async def get_cars_by_pipeline(session: AsyncSession, status: Optional[str] = None) -> List[Car]:
    """Get cars by pipeline status"""
    query = select(Car).where(Car.is_available == True)
    if status:
        query = query.where(Car.pipeline_status == status)
    query = query.order_by(Car.pipeline_updated_at.desc().nullslast(), Car.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def increment_car_views(session: AsyncSession, car_id: int):
    """Increment car view count"""
    await session.execute(
        update(Car).where(Car.id == car_id).values(views_count=Car.views_count + 1)
    )
    await session.commit()


# ====== SUBSCRIPTION CRUD ======

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


# ====== INQUIRY CRUD ======

async def create_inquiry(session: AsyncSession, user_id: int, inquiry_type: str, **kwargs) -> Inquiry:
    """Create customer inquiry with lead scoring"""
    inquiry = Inquiry(user_id=user_id, inquiry_type=inquiry_type, **kwargs)
    session.add(inquiry)
    await session.commit()
    await session.refresh(inquiry)
    logger.info(f"New inquiry created: {inquiry_type} from user {user_id} (Score: {inquiry.lead_score})")
    return inquiry


async def get_pending_inquiries(session: AsyncSession) -> List[Inquiry]:
    """Get pending inquiries for admin — sorted by lead score (highest first)"""
    result = await session.execute(
        select(Inquiry)
        .where(Inquiry.status.in_(["pending", "processing"]))
        .order_by(Inquiry.lead_score.desc(), Inquiry.created_at.desc())
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


async def get_inquiries_needing_followup(session: AsyncSession) -> List[Inquiry]:
    """Get inquiries that need follow-up"""
    now = datetime.utcnow()
    result = await session.execute(
        select(Inquiry).where(
            Inquiry.status.in_(["pending", "processing"]),
            or_(
                Inquiry.next_followup_at.is_(None),
                Inquiry.next_followup_at <= now
            )
        ).order_by(Inquiry.lead_score.desc())
    )
    return list(result.scalars().all())


# ====== BUY REQUEST CRUD ======

async def create_buy_request(session: AsyncSession, user_id: int, **kwargs) -> BuyRequest:
    """Create buy request"""
    buy_request = BuyRequest(user_id=user_id, **kwargs)
    session.add(buy_request)
    await session.commit()
    await session.refresh(buy_request)
    logger.info(f"New buy request from user {user_id}: {kwargs.get('brand', '?')} {kwargs.get('model', '?')}")
    return buy_request


async def get_pending_buy_requests(session: AsyncSession) -> List[BuyRequest]:
    """Get pending buy requests — sorted by score"""
    result = await session.execute(
        select(BuyRequest)
        .where(BuyRequest.status.in_(["pending", "searching"]))
        .order_by(BuyRequest.lead_score.desc(), BuyRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def get_buy_request_by_id(session: AsyncSession, request_id: int) -> Optional[BuyRequest]:
    """Get buy request by ID"""
    result = await session.execute(select(BuyRequest).where(BuyRequest.id == request_id))
    return result.scalar_one_or_none()


async def update_buy_request_status(session: AsyncSession, request_id: int, status: str, admin_notes: Optional[str] = None):
    """Update buy request status"""
    values = {"status": status, "updated_at": datetime.utcnow()}
    if admin_notes:
        values["admin_notes"] = admin_notes
    await session.execute(
        update(BuyRequest).where(BuyRequest.id == request_id).values(**values)
    )
    await session.commit()


async def get_user_buy_requests(session: AsyncSession, user_id: int) -> List[BuyRequest]:
    """Get user's buy requests"""
    result = await session.execute(
        select(BuyRequest).where(BuyRequest.user_id == user_id).order_by(BuyRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def find_matching_cars_for_request(session: AsyncSession, request: BuyRequest) -> List[Car]:
    """Find cars matching a buy request"""
    query = select(Car).where(Car.is_available == True)
    
    if request.brand:
        query = query.where(Car.brand.ilike(f"%{request.brand}%"))
    if request.model:
        query = query.where(Car.model.ilike(f"%{request.model}%"))
    if request.year_from:
        query = query.where(Car.year >= request.year_from)
    if request.year_to:
        query = query.where(Car.year <= request.year_to)
    if request.budget_min:
        query = query.where(Car.price >= request.budget_min)
    if request.budget_max:
        query = query.where(Car.price <= request.budget_max)
    if request.transmission:
        query = query.where(Car.transmission.ilike(f"%{request.transmission}%"))
    
    query = query.order_by(Car.created_at.desc()).limit(10)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_buy_requests_needing_followup(session: AsyncSession) -> List[BuyRequest]:
    """Get buy requests needing follow-up"""
    now = datetime.utcnow()
    result = await session.execute(
        select(BuyRequest).where(
            BuyRequest.status.in_(["pending", "searching", "found_options"]),
            or_(
                BuyRequest.next_followup_at.is_(None),
                BuyRequest.next_followup_at <= now
            )
        ).order_by(BuyRequest.lead_score.desc())
    )
    return list(result.scalars().all())


# ====== FOLLOW-UP CRUD ======

async def create_followup(session: AsyncSession, **kwargs) -> FollowUp:
    """Create a follow-up entry"""
    followup = FollowUp(**kwargs)
    session.add(followup)
    await session.commit()
    await session.refresh(followup)
    return followup


async def get_pending_followups(session: AsyncSession) -> List[FollowUp]:
    """Get pending follow-ups that need to be sent"""
    now = datetime.utcnow()
    result = await session.execute(
        select(FollowUp).where(
            FollowUp.is_sent == False,
            FollowUp.scheduled_at <= now
        ).order_by(FollowUp.scheduled_at.asc())
    )
    return list(result.scalars().all())


async def mark_followup_sent(session: AsyncSession, followup_id: int):
    """Mark follow-up as sent"""
    await session.execute(
        update(FollowUp).where(FollowUp.id == followup_id).values(
            is_sent=True,
            sent_at=datetime.utcnow()
        )
    )
    await session.commit()


async def schedule_followups_for_inquiry(session: AsyncSession, inquiry_id: int, user_id: int):
    """Schedule automatic follow-ups for an inquiry"""
    now = datetime.utcnow()
    
    followups = [
        # 1 soatdan keyin — ariza qabul qilindi
        FollowUp(
            user_id=user_id,
            target_type="inquiry",
            target_id=inquiry_id,
            message_type="received",
            message_text="✅ Arizangiz qabul qilindi! Mutaxassislarimiz ko'rib chiqmoqda. Tez orada siz bilan bog'lanamiz. 📞",
            scheduled_at=now + timedelta(minutes=5),  # 5 minutdan keyin
        ),
        # 24 soat — eslatma
        FollowUp(
            user_id=user_id,
            target_type="inquiry",
            target_id=inquiry_id,
            message_type="reminder_24h",
            message_text="👋 Assalomu alaykum! Arizangiz bo'yicha ishlamoqdamiz. Mutaxassislarimiz tez orada siz bilan aloqaga chiqadi. Sabringiz uchun rahmat! 🙏",
            scheduled_at=now + timedelta(hours=24),
        ),
        # 3 kundan keyin — follow-up
        FollowUp(
            user_id=user_id,
            target_type="inquiry",
            target_id=inquiry_id,
            message_type="followup_3d",
            message_text="🚗 Qanday ahvol? Moshina masalasi hal bo'ldimi? Agar savollaringiz bo'lsa, biz doim yordamga tayyormiz! \n\n📞 Admin: @avtosavdo_admin",
            scheduled_at=now + timedelta(days=3),
        ),
        # 7 kundan keyin — boshqa variant kerakmi
        FollowUp(
            user_id=user_id,
            target_type="inquiry",
            target_id=inquiry_id,
            message_type="followup_7d",
            message_text="🌟 Sizga boshqa moshina variantlari kerakmi? Yangi takliflarimiz bor!\n\nKatalogni ko'rish uchun /start bosing yoki to'g'ridan-to'g'ri yozing: @avtosavdo_admin 📲",
            scheduled_at=now + timedelta(days=7),
        ),
    ]
    
    for fu in followups:
        session.add(fu)
    
    await session.commit()


async def schedule_followups_for_buy_request(session: AsyncSession, request_id: int, user_id: int):
    """Schedule automatic follow-ups for a buy request"""
    now = datetime.utcnow()
    
    followups = [
        FollowUp(
            user_id=user_id,
            target_type="buy_request",
            target_id=request_id,
            message_type="received",
            message_text="✅ Sizning sotib olish arizangiz qabul qilindi! Mos variantlarni qidirib topamiz va darhol sizga xabar beramiz. 🔍",
            scheduled_at=now + timedelta(minutes=5),
        ),
        FollowUp(
            user_id=user_id,
            target_type="buy_request",
            target_id=request_id,
            message_type="reminder_24h",
            message_text="🔍 Sizning moshina qidiruvingiz davom etmoqda! Bozordagi eng yaxshi takliflarni tanlamoqdamiz. Tez orada natijalar tayyob bo'ladi! 🚗",
            scheduled_at=now + timedelta(hours=24),
        ),
        FollowUp(
            user_id=user_id,
            target_type="buy_request",
            target_id=request_id,
            message_type="followup_3d",
            message_text="🚗 Assalomu alaykum! Moshina qidiruvi davom etmoqda. Agar kriteryalaringizni o'zgartirmoqchi bo'lsangiz, bizga yozing!\n\n📞 @avtosavdo_admin",
            scheduled_at=now + timedelta(days=3),
        ),
    ]
    
    for fu in followups:
        session.add(fu)
    
    await session.commit()


# ====== CONTACT LOG CRUD ======

async def create_contact_log(session: AsyncSession, admin_id: int, user_id: int,
                             contact_type: str, notes: Optional[str] = None,
                             result: Optional[str] = None) -> ContactLog:
    """Log a contact between admin and user"""
    log = ContactLog(
        admin_id=admin_id,
        user_id=user_id,
        contact_type=contact_type,
        notes=notes,
        result=result
    )
    session.add(log)
    
    # Update user's last_contacted_at
    await session.execute(
        update(User).where(User.telegram_id == user_id).values(
            last_contacted_at=datetime.utcnow()
        )
    )
    
    await session.commit()
    await session.refresh(log)
    return log


async def get_contact_history(session: AsyncSession, user_id: int, limit: int = 10) -> List[ContactLog]:
    """Get contact history for a user"""
    result = await session.execute(
        select(ContactLog)
        .where(ContactLog.user_id == user_id)
        .order_by(ContactLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ====== SOLD CAR CRUD ======

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


# ====== SCRAPED LISTING CRUD ======

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


async def check_listing_status(session: AsyncSession, external_id: str, new_price: float) -> dict:
    """Check if listing exists and if price changed"""
    result = await session.execute(
        select(ScrapedListing).where(ScrapedListing.external_id == external_id)
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        return {'exists': False, 'price_changed': False, 'old_price': 0}
    
    existing.scraped_at = datetime.utcnow()
    
    if abs(existing.price - new_price) > 1:
        old_price = existing.price
        existing.price = new_price
        existing.is_processed = False
        await session.commit()
        
        diff = old_price - new_price
        change_type = "dropped" if diff > 0 else "increased"
        
        return {
            'exists': True, 
            'price_changed': True, 
            'old_price': old_price, 
            'change_type': change_type,
            'diff': abs(diff)
        }
    
    await session.commit()
    return {'exists': True, 'price_changed': False, 'old_price': existing.price}


def extract_position(text: Optional[str]) -> Optional[str]:
    """Extract car position/trim from description text"""
    if not text:
        return None
    text = text.lower()
    
    if 'premier' in text: return 'premier'
    if 'redline' in text: return 'redline'
    if 'style' in text: return 'style'
    if 'elegant' in text: return 'elegant'
    if 'plus' in text: return 'plus'
    if 'ltoz' in text or 'ltz' in text: return 'ltz'
    if ' ls ' in text: return 'ls'
    if ' lt ' in text: return 'lt'
    
    pos_match = re.search(r'\b(\d)\s*[-]?\s*(poz|evro)', text)
    if pos_match:
        return f"{pos_match.group(1)}-pozitsiya"
        
    if 'full' in text: return 'full'
    return None


async def get_average_market_price(
    session: AsyncSession, 
    brand: str, 
    model: str, 
    year: int, 
    transmission: Optional[str] = None,
    mileage: Optional[int] = None,
    description: Optional[str] = None
) -> float:
    """Calculate TRUE market price for Flipper Mode"""
    
    query = select(ScrapedListing.price, ScrapedListing.description, ScrapedListing.mileage).where(
        and_(
            func.lower(ScrapedListing.brand) == brand.lower(),
            func.lower(ScrapedListing.model) == model.lower(),
            ScrapedListing.year == year,
            ScrapedListing.price > 2000
        )
    )
    
    if transmission:
        if transmission.lower() in ['avtomat', 'automatic']:
             query = query.where(func.lower(ScrapedListing.transmission).in_(['avtomat', 'automatic']))
        elif transmission.lower() in ['mexanika', 'manual']:
             query = query.where(func.lower(ScrapedListing.transmission).in_(['mexanika', 'manual']))

    result = await session.execute(query)
    rows = result.all()
    
    if not rows:
        return 0.0

    filtered_prices = []
    target_position = extract_position(description)
    
    for row in rows:
        r_price, r_desc, r_mileage = row
        
        if target_position:
            r_pos = extract_position(r_desc)
            if r_pos and r_pos != target_position:
                continue
        
        if mileage and r_mileage:
            diff = abs(mileage - r_mileage)
            if mileage < 10000:
                if r_mileage > 20000: continue
            else:
                if diff > 30000: continue
        
        filtered_prices.append(r_price)
    
    if len(filtered_prices) < 3:
        filtered_prices = [r[0] for r in rows]
        
    if not filtered_prices:
        return 0.0
        
    filtered_prices.sort()
    count = len(filtered_prices)
    
    if count > 5:
        trim_count = int(count * 0.1)
        filtered_prices = filtered_prices[trim_count : count - trim_count]
        
    if not filtered_prices:
        return 0.0
        
    avg_price = sum(filtered_prices) / len(filtered_prices)
    return round(avg_price, 0)


async def get_price_range(session: AsyncSession, brand: str, model: str, year: int) -> dict:
    """Get min, max, avg price for a specific car"""
    result = await session.execute(
        select(
            func.min(ScrapedListing.price).label('min_price'),
            func.max(ScrapedListing.price).label('max_price'),
            func.avg(ScrapedListing.price).label('avg_price'),
            func.count(ScrapedListing.id).label('count')
        ).where(
            and_(
                func.lower(ScrapedListing.brand) == brand.lower(),
                func.lower(ScrapedListing.model) == model.lower(),
                ScrapedListing.year == year,
                ScrapedListing.price > 2000,
                ScrapedListing.scraped_at >= datetime.utcnow() - timedelta(days=14)
            )
        )
    )
    row = result.one_or_none()
    if row and row.count > 0:
        return {
            'min_price': float(row.min_price),
            'max_price': float(row.max_price),
            'avg_price': float(row.avg_price),
            'count': row.count
        }
    return {'min_price': 0, 'max_price': 0, 'avg_price': 0, 'count': 0}


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


# ====== FAVORITE CRUD ======

async def add_to_favorites(session: AsyncSession, user_id: int, car_id: int) -> bool:
    """Add car to user's favorites"""
    result = await session.execute(
        select(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.car_id == car_id)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return False
    
    favorite = Favorite(user_id=user_id, car_id=car_id)
    session.add(favorite)
    await session.commit()
    return True


async def remove_from_favorites(session: AsyncSession, user_id: int, car_id: int):
    """Remove car from user's favorites"""
    await session.execute(
        delete(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.car_id == car_id)
        )
    )
    await session.commit()


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


# ====== REVIEW CRUD ======

async def create_review(session: AsyncSession, user_id: int, car_id: int, rating: int, comment: Optional[str] = None):
    """Create car review"""
    result = await session.execute(
        select(Review).where(
            and_(Review.user_id == user_id, Review.car_id == car_id)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.rating = rating
        existing.comment = comment
        existing.created_at = datetime.utcnow()
        await session.commit()
        return existing
    
    review = Review(user_id=user_id, car_id=car_id, rating=rating, comment=comment)
    session.add(review)
    await session.commit()
    await session.refresh(review)
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
        select(func.avg(Review.rating)).where(Review.car_id == car_id)
    )
    avg_rating = result.scalar_one_or_none()
    return float(avg_rating) if avg_rating else 0.0


async def get_car_review_count(session: AsyncSession, car_id: int) -> int:
    """Get review count for a car"""
    result = await session.execute(
        select(func.count(Review.id)).where(Review.car_id == car_id)
    )
    return result.scalar_one_or_none() or 0


async def get_active_competitors_count(session: AsyncSession, brand: str, model: str, year: int, price: float) -> int:
    """Count direct competitors"""
    lower_bound = price * 0.85
    upper_bound = price * 1.15
    
    result = await session.execute(
        select(func.count(ScrapedListing.id)).where(
            and_(
                func.lower(ScrapedListing.brand) == brand.lower(),
                func.lower(ScrapedListing.model) == model.lower(),
                ScrapedListing.year == year,
                ScrapedListing.price >= lower_bound,
                ScrapedListing.price <= upper_bound,
                ScrapedListing.scraped_at >= datetime.utcnow() - timedelta(days=7)
            )
        )
    )
    return result.scalar_one_or_none() or 0


async def find_similar_listing(session: AsyncSession, brand: str, model: str, year: int, price: float, current_source: str) -> Optional[ScrapedListing]:
    """Find same car from different source"""
    time_limit = datetime.utcnow() - timedelta(days=5)
    
    result = await session.execute(
        select(ScrapedListing).where(
            and_(
                ScrapedListing.source != current_source,
                func.lower(ScrapedListing.brand) == brand.lower(),
                func.lower(ScrapedListing.model) == model.lower(),
                ScrapedListing.year == year,
                ScrapedListing.price >= price * 0.98,
                ScrapedListing.price <= price * 1.02,
                ScrapedListing.scraped_at >= time_limit
            )
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def get_good_deals(session: AsyncSession, limit: int = 10) -> List[ScrapedListing]:
    """Get top rated good deals"""
    stmt = (
        select(ScrapedListing)
        .where(
             ScrapedListing.is_good_deal == True,
             ScrapedListing.scraped_at >= datetime.utcnow() - timedelta(days=5)
        )
        .order_by(ScrapedListing.deal_score.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_market_stats(session: AsyncSession) -> dict:
    """Get overall market statistics"""
    stats = {
        'total_listings': 0,
        'new_today': 0,
        'avg_prices': {},
        'total_users': 0,
        'pending_inquiries': 0,
        'pending_buy_requests': 0,
        'active_subscriptions': 0
    }
    
    # Total listings
    total_res = await session.execute(
        select(func.count(ScrapedListing.id))
        .where(ScrapedListing.scraped_at >= datetime.utcnow() - timedelta(days=7))
    )
    stats['total_listings'] = total_res.scalar_one_or_none() or 0
    
    # New today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_res = await session.execute(
        select(func.count(ScrapedListing.id)).where(ScrapedListing.scraped_at >= today_start)
    )
    stats['new_today'] = new_res.scalar_one_or_none() or 0
    
    # Total users
    user_res = await session.execute(select(func.count(User.id)))
    stats['total_users'] = user_res.scalar_one_or_none() or 0
    
    # Pending inquiries
    inq_res = await session.execute(
        select(func.count(Inquiry.id)).where(Inquiry.status == "pending")
    )
    stats['pending_inquiries'] = inq_res.scalar_one_or_none() or 0
    
    # Pending buy requests
    buy_res = await session.execute(
        select(func.count(BuyRequest.id)).where(BuyRequest.status == "pending")
    )
    stats['pending_buy_requests'] = buy_res.scalar_one_or_none() or 0
    
    # Active subscriptions
    sub_res = await session.execute(
        select(func.count(Subscription.id)).where(Subscription.is_active == True)
    )
    stats['active_subscriptions'] = sub_res.scalar_one_or_none() or 0
    
    # Avg price for popular models
    models = ['gentra', 'cobalt', 'nexia', 'spark', 'malibu']
    for m in models:
        avg_res = await session.execute(
            select(func.avg(ScrapedListing.price)).where(
                and_(
                    func.lower(ScrapedListing.model).like(f"%{m}%"),
                    ScrapedListing.scraped_at >= datetime.utcnow() - timedelta(days=7),
                    ScrapedListing.price > 1000
                )
            )
        )
        avg_val = avg_res.scalar_one_or_none()
        if avg_val:
            stats['avg_prices'][m.capitalize()] = float(avg_val)
            
    return stats


async def convert_inquiry_to_car(
    session: AsyncSession, 
    inquiry_id: int, 
    price: float,
    brand: str,
    model: str,
    year: int,
    description: str,
    images: list,
    mileage: int = 0,
    color: str = None
) -> Optional[Car]:
    """Convert valid inquiry to car listing with edited details"""
    stmt = select(Inquiry).where(Inquiry.id == inquiry_id)
    result = await session.execute(stmt)
    inquiry = result.scalar_one_or_none()
    
    if not inquiry: return None
    
    # Ensure images format
    final_images = images
    if isinstance(images, list):
         final_images = {'gallery': images}
    
    new_car = Car(
        brand=brand,
        model=model,
        year=year,
        price=price,
        description=description,
        images=final_images,
        mileage=mileage,
        color=color,
        is_available=True,
        source="inquiry",
        external_id=f"inquiry_{inquiry.id}",
        pipeline_status="qabul"
    )
    session.add(new_car)
    
    inquiry.status = "completed"
    await session.commit()
    await session.refresh(new_car)
    return new_car


# ====== DASHBOARD STATS ======

async def get_admin_dashboard_stats(session: AsyncSession) -> dict:
    """Full admin dashboard statistics"""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Users
    total_users_res = await session.execute(select(func.count(User.id)))
    active_users_res = await session.execute(
        select(func.count(User.id)).where(User.last_activity >= week_ago)
    )
    new_users_res = await session.execute(
        select(func.count(User.id)).where(User.created_at >= month_ago)
    )
    hot_leads_res = await session.execute(
        select(func.count(User.id)).where(User.lead_score >= 60, User.is_admin == False)
    )
    
    # Cars
    total_cars_res = await session.execute(select(func.count(Car.id)).where(Car.is_available == True))
    
    # Inquiries
    pending_inq_res = await session.execute(
        select(func.count(Inquiry.id)).where(Inquiry.status == "pending")
    )
    total_inq_month_res = await session.execute(
        select(func.count(Inquiry.id)).where(Inquiry.created_at >= month_ago)
    )
    
    # Buy Requests
    pending_buy_res = await session.execute(
        select(func.count(BuyRequest.id)).where(BuyRequest.status == "pending")
    )
    
    # Sold
    sold_month_res = await session.execute(
        select(func.count(SoldCar.id)).where(SoldCar.sold_at >= month_ago)
    )
    profit_month_res = await session.execute(
        select(func.sum(SoldCar.profit)).where(SoldCar.sold_at >= month_ago)
    )
    
    return {
        'total_users': total_users_res.scalar_one_or_none() or 0,
        'active_users_7d': active_users_res.scalar_one_or_none() or 0,
        'new_users_30d': new_users_res.scalar_one_or_none() or 0,
        'hot_leads': hot_leads_res.scalar_one_or_none() or 0,
        'total_cars': total_cars_res.scalar_one_or_none() or 0,
        'pending_inquiries': pending_inq_res.scalar_one_or_none() or 0,
        'total_inquiries_30d': total_inq_month_res.scalar_one_or_none() or 0,
        'pending_buy_requests': pending_buy_res.scalar_one_or_none() or 0,
        'sold_30d': sold_month_res.scalar_one_or_none() or 0,
        'profit_30d': float(profit_month_res.scalar_one_or_none() or 0),
    }
