"""
Database models for the car sales bot
Enhanced with Lead Scoring, Pipeline, Follow-up, Buy Requests
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class User(Base):
    """User model — enhanced with lead scoring and segmentation"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Lead scoring / Segmentation
    lead_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100, jiddiylik bali
    preferred_brands: Mapped[Optional[str]] = mapped_column(Text)  # CSV: "Chevrolet,Hyundai"
    budget_min: Mapped[Optional[float]] = mapped_column(Float)
    budget_max: Mapped[Optional[float]] = mapped_column(Float)
    total_views: Mapped[int] = mapped_column(Integer, default=0)  # jami moshinlarni ko'rish
    total_inquiries: Mapped[int] = mapped_column(Integer, default=0)  # jami murojaatlar soni
    conversion_status: Mapped[str] = mapped_column(String(50), default="yangi")
    # yangi → qiziqmoqda → muzokara → sotib_oldi → qaytdi
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)  # Admin eslatmalari
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source: Mapped[Optional[str]] = mapped_column(String(50))  # telegram, instagram, referral
    
    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_lead_score", "lead_score"),
        Index("idx_user_conversion", "conversion_status"),
    )


class Car(Base):
    """Car model for listings"""
    __tablename__ = "cars"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mileage: Mapped[Optional[int]] = mapped_column(Integer)
    color: Mapped[Optional[str]] = mapped_column(String(50))
    condition: Mapped[Optional[str]] = mapped_column(String(50))  # yangi, ideal, yaxshi, o'rtacha
    transmission: Mapped[Optional[str]] = mapped_column(String(50))  # avtomat, mexanika
    fuel_type: Mapped[Optional[str]] = mapped_column(String(50))  # benzin, dizel, gaz, gibrid, elektr
    description: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[Optional[dict]] = mapped_column(JSON)  # list of image URLs
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Expert evaluation
    expert_notes: Mapped[Optional[str]] = mapped_column(Text)  # Dadaning xulosasi
    market_price: Mapped[Optional[float]] = mapped_column(Float)  # Bozor narxi
    
    # Source tracking
    source: Mapped[Optional[str]] = mapped_column(String(50))  # olx, avtoelon, manual
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    external_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Pipeline tracking
    pipeline_status: Mapped[str] = mapped_column(String(50), default="qabul")
    # qabul → rasm_olindi → kanalga_joylandi → korishlar → telefon → kelishildi → sotildi
    pipeline_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_car_brand_model", "brand", "model"),
        Index("idx_car_price", "price"),
        Index("idx_car_pipeline", "pipeline_status"),
        Index("idx_car_available", "is_available"),
    )


class SoldCar(Base):
    """Sold cars for analytics"""
    __tablename__ = "sold_cars"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)
    sold_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    buyer_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    days_to_sell: Mapped[Optional[int]] = mapped_column(Integer)  # necha kunda sotildi

    __table_args__ = (
        Index("idx_sold_date", "sold_at"),
    )


class Subscription(Base):
    """User subscriptions for car alerts"""
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    
    # Search criteria
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    year_from: Mapped[Optional[int]] = mapped_column(Integer)
    year_to: Mapped[Optional[int]] = mapped_column(Integer)
    price_from: Mapped[Optional[float]] = mapped_column(Float)
    price_to: Mapped[Optional[float]] = mapped_column(Float)
    condition: Mapped[Optional[str]] = mapped_column(String(50))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notification_count: Mapped[int] = mapped_column(Integer, default=0)  # nechta notification borgan
    
    # Relationship
    user: Mapped["User"] = relationship(back_populates="subscriptions")

    __table_args__ = (
        Index("idx_sub_brand", "brand"),
        Index("idx_sub_model", "model"),
        Index("idx_sub_price", "price_to"),
    )


class Inquiry(Base):
    """Customer inquiries and pre-orders"""
    __tablename__ = "inquiries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    inquiry_type: Mapped[str] = mapped_column(String(50), nullable=False)  # buy, sell, question
    
    # Car details (if selling or buying)
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Lead info
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, rejected
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Follow-up tracking
    followup_count: Mapped[int] = mapped_column(Integer, default=0)  # nechta follow-up borgan
    last_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationship
    user: Mapped["User"] = relationship(back_populates="inquiries")
    
    __table_args__ = (
        Index("idx_inquiry_status", "status"),
        Index("idx_inquiry_urgency", "urgency"),
    )


class BuyRequest(Base):
    """Buy requests — klient moshina olmoqchi"""
    __tablename__ = "buy_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    
    # Xohlagan moshina
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    year_from: Mapped[Optional[int]] = mapped_column(Integer)
    year_to: Mapped[Optional[int]] = mapped_column(Integer)
    budget_min: Mapped[Optional[float]] = mapped_column(Float)
    budget_max: Mapped[Optional[float]] = mapped_column(Float)
    preferred_color: Mapped[Optional[str]] = mapped_column(String(50))
    transmission: Mapped[Optional[str]] = mapped_column(String(50))
    fuel_type: Mapped[Optional[str]] = mapped_column(String(50))
    max_mileage: Mapped[Optional[int]] = mapped_column(Integer)
    additional_notes: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending → searching → found_options → contacted → completed
    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Matching
    matched_cars: Mapped[Optional[dict]] = mapped_column(JSON)  # [{car_id, sent_at}, ...]
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Follow-up
    followup_count: Mapped[int] = mapped_column(Integer, default=0)
    last_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_buyreq_status", "status"),
    )


class FollowUp(Base):
    """Follow-up log — har bir follow-up qayd qilinadi"""
    __tablename__ = "followups"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # inquiry, buy_request
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # received, reminder_1h, reminder_24h, followup_3d, followup_7d, custom
    message_text: Mapped[Optional[str]] = mapped_column(Text)
    
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # qachon yuborilishi kerak
    
    __table_args__ = (
        Index("idx_followup_scheduled", "scheduled_at"),
        Index("idx_followup_sent", "is_sent"),
    )


class Favorite(Base):
    """User favorites"""
    __tablename__ = "favorites"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    car_id: Mapped[int] = mapped_column(Integer, ForeignKey("cars.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    car: Mapped["Car"] = relationship()


class Review(Base):
    """User reviews and ratings"""
    __tablename__ = "reviews"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    car_id: Mapped[int] = mapped_column(Integer, ForeignKey("cars.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship()
    car: Mapped["Car"] = relationship()


class ScrapedListing(Base):
    """Scraped listings from OLX and Avtoelon"""
    __tablename__ = "scraped_listings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # olx, avtoelon
    external_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mileage: Mapped[Optional[int]] = mapped_column(Integer)  # Probeg
    description: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    color: Mapped[Optional[str]] = mapped_column(String(50))
    transmission: Mapped[Optional[str]] = mapped_column(String(50))
    fuel_type: Mapped[Optional[str]] = mapped_column(String(50))
    images: Mapped[Optional[dict]] = mapped_column(JSON)
    
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_good_deal: Mapped[bool] = mapped_column(Boolean, default=False)  # Arzon variant
    notified_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    deal_score: Mapped[int] = mapped_column(Integer, default=50)
    
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_scraped_external", "external_id"),
        Index("idx_scraped_processed", "is_processed"),
        Index("idx_scraped_good_deal", "is_good_deal"),
    )


class ContactLog(Base):
    """Contact history — admin bilan mijoz orasidagi aloqa tarixi"""
    __tablename__ = "contact_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False)  # call, message, meeting
    notes: Mapped[Optional[str]] = mapped_column(Text)
    result: Mapped[Optional[str]] = mapped_column(String(100))  # interested, not_interested, callback, deal_made
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KonkursParticipant(Base):
    """Konkurs ishtirokchilari jadvali"""
    __tablename__ = "konkurs_participants"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True)
    referred_by_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    referrer: Mapped[Optional["User"]] = relationship(foreign_keys=[referred_by_id])
