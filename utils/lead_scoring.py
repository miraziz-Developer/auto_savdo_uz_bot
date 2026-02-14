"""
Lead Scoring Engine — Mijozni aqlli baholash tizimi
Har bir murojaatga va foydalanuvchiga avtomatik ball beradi
"""
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import User, Inquiry, BuyRequest, Subscription, Favorite


async def calculate_user_lead_score(session: AsyncSession, user_id: int) -> int:
    """
    Foydalanuvchining jiddiylik ballini hisoblash.
    0-100 oralig'ida ball.
    """
    score = 0
    
    # 1. User info completeness
    user_result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return 0
    
    # Telefon raqam qoldirgan (+20)
    if user.phone:
        score += 20
    
    # Username bormi (+5)
    if user.username:
        score += 5
    
    # 2. Activity level
    # Jami ko'rishlar soni
    if user.total_views >= 20:
        score += 15
    elif user.total_views >= 10:
        score += 10
    elif user.total_views >= 3:
        score += 5
    
    # 3. Inquiry history
    inq_count = await session.execute(
        select(func.count(Inquiry.id)).where(Inquiry.user_id == user_id)
    )
    inquiry_count = inq_count.scalar_one_or_none() or 0
    if inquiry_count >= 3:
        score += 15
    elif inquiry_count >= 1:
        score += 10
    
    # 4. Buy requests
    buy_count = await session.execute(
        select(func.count(BuyRequest.id)).where(BuyRequest.user_id == user_id)
    )
    buy_request_count = buy_count.scalar_one_or_none() or 0
    if buy_request_count >= 1:
        score += 15  # Aktiv sotib oluvchi
    
    # 5. Subscriptions (obuna qilgan)
    sub_count = await session.execute(
        select(func.count(Subscription.id)).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        )
    )
    subscription_count = sub_count.scalar_one_or_none() or 0
    if subscription_count >= 1:
        score += 10
    
    # 6. Favorites (sevimlilar)
    fav_count = await session.execute(
        select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    )
    favorite_count = fav_count.scalar_one_or_none() or 0
    if favorite_count >= 3:
        score += 10
    elif favorite_count >= 1:
        score += 5
    
    # 7. Recency bonus — so'nggi 3 kun ichida faol bo'lgan
    if user.last_activity and (datetime.utcnow() - user.last_activity).days <= 3:
        score += 10
    
    # Cap at 100
    score = min(100, max(0, score))
    
    # Update user's lead score
    user.lead_score = score
    user.total_inquiries = inquiry_count + buy_request_count
    await session.commit()
    
    return score


def calculate_inquiry_lead_score(
    has_phone: bool = False,
    has_budget: bool = False,
    has_images: bool = False,
    is_returning: bool = False,
    has_specific_model: bool = False,
    urgency_keywords: bool = False,
    user_lead_score: int = 0
) -> tuple[int, str]:
    """
    Murojaat (inquiry) uchun ball hisoblash.
    Returns: (score, urgency)
    """
    score = 0
    
    # Phone (+25) — eng muhim signal
    if has_phone:
        score += 25
    
    # Budget specified (+15)
    if has_budget:
        score += 15
    
    # Images provided (+10)
    if has_images:
        score += 10
    
    # Returning client (+15)
    if is_returning:
        score += 15
    
    # Specific model (+10)
    if has_specific_model:
        score += 10
    
    # Urgency keywords (+15)
    if urgency_keywords:
        score += 15
    
    # User's general score influence (+10)
    if user_lead_score >= 70:
        score += 10
    elif user_lead_score >= 40:
        score += 5
    
    score = min(100, max(0, score))
    
    # Determine urgency
    if score >= 80:
        urgency = "urgent"
    elif score >= 60:
        urgency = "high"
    elif score >= 35:
        urgency = "normal"
    else:
        urgency = "low"
    
    return score, urgency


def get_urgency_emoji(urgency: str) -> str:
    """Get emoji for urgency level"""
    return {
        "urgent": "🔴",
        "high": "🟠",
        "normal": "🟡",
        "low": "🟢"
    }.get(urgency, "⚪")


def get_urgency_text(urgency: str) -> str:
    """Get human-readable urgency text"""
    return {
        "urgent": "SHOSHILINCH — Darhol bog'laning!",
        "high": "YUQORI — Bugun bog'laning",
        "normal": "O'RTACHA — 24 soat ichida",
        "low": "PAST — Qaytib kelishi mumkin"
    }.get(urgency, "Noma'lum")


def detect_urgency_keywords(text: str) -> bool:
    """Matnda shoshilinch so'zlar borligini tekshirish"""
    if not text:
        return False
    text = text.lower()
    keywords = [
        'srochno', 'tez', 'shoshilinch', 'bugun', 'hozir',
        'zudlik', 'zarur', 'tezroq', 'kerak', 'darhol',
        'pul tayyor', 'naqd tayyor', 'olmoqchiman', 'sotmoqchiman',
        'urgent', 'asap'
    ]
    return any(kw in text for kw in keywords)


def get_lead_score_emoji(score: int) -> str:
    """Score uchun emoji"""
    if score >= 80:
        return "🔥🔥🔥"
    elif score >= 60:
        return "🔥🔥"
    elif score >= 40:
        return "🔥"
    elif score >= 20:
        return "⭐"
    else:
        return "❄️"
