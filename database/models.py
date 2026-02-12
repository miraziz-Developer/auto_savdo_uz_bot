"""
Database models for the car sales bot
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class User(Base):
    """User model for customers"""
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
    
    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="user", cascade="all, delete-orphan")


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
    
    # Relationship
    user: Mapped["User"] = relationship(back_populates="subscriptions")


class Inquiry(Base):
    """Customer inquiries and pre-orders"""
    __tablename__ = "inquiries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    inquiry_type: Mapped[str] = mapped_column(String(50), nullable=False)  # buy, sell, question
    
    # Car details (if selling)
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[Optional[dict]] = mapped_column(JSON)
    
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, rejected
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user: Mapped["User"] = relationship(back_populates="inquiries")


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
    
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
