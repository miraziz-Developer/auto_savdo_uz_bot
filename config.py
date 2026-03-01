"""
Configuration settings for the car sales bot
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore undefined env vars
    )
    
    # Bot Configuration
    bot_token: str = Field(..., alias="BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    payment_provider_token: str = Field(default="", alias="PAYMENT_PROVIDER_TOKEN")
    
    # Database
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="avtosavdo", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    
    # Direct URL (from Render/Railway)
    database_url_env: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_url_env: Optional[str] = Field(default=None, alias="REDIS_URL")
    
    # Channels
    telegram_channel_id: str = Field(default="", alias="TELEGRAM_CHANNEL_ID")
    scraped_deals_channel_id: str = Field(default="", alias="SCRAPED_DEALS_CHANNEL_ID")
    admin_cars_channel_id: str = Field(default="", alias="ADMIN_CARS_CHANNEL_ID")
    admin_group_id: str = Field(default="", alias="ADMIN_GROUP_ID")
    instagram_api_token: str = Field(default="", alias="INSTAGRAM_API_TOKEN")
    
    # Scraping
    scraping_interval: int = Field(default=60, alias="SCRAPING_INTERVAL")
    user_agents_rotation: bool = Field(default=True, alias="USER_AGENTS_ROTATION")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")
    
    # Notifications
    enable_push_notifications: bool = Field(default=True, alias="ENABLE_PUSH_NOTIFICATIONS")
    weekly_push_day: str = Field(default="monday", alias="WEEKLY_PUSH_DAY")
    weekly_push_time: str = Field(default="09:00", alias="WEEKLY_PUSH_TIME")

    # MinIO / S3 Storage
    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(default="avtosavdo-images", alias="MINIO_BUCKET_NAME")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # Monitoring (Sentry)
    sentry_dsn: Optional[str] = Field(default="", alias="SENTRY_DSN")
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection string"""
        if self.database_url_env:
            # Fix for SQLAlchemy: replace postgres:// with postgresql+asyncpg://
            url = self.database_url_env
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                 url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
            
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def database_url_sync(self) -> str:
        """PostgreSQL connection string (Sync)"""
        if self.database_url_env:
            url = self.database_url_env
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql://", 1)
            return url
            
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Redis connection string"""
        if self.redis_url_env:
            return self.redis_url_env
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def admin_list(self) -> List[int]:
        """Parse admin IDs from comma-separated string"""
        if not self.admin_ids:
            return []
        try:
            return [int(admin_id.strip()) for admin_id in self.admin_ids.split(",")]
        except ValueError:
            return []

# Global settings instance
settings = Settings()
