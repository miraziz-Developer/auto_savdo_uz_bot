"""
Configuration settings for the car sales bot
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Bot Configuration
    bot_token: str = Field(..., alias="BOT_TOKEN")
    admin_ids: str = Field(..., alias="ADMIN_IDS")
    payment_provider_token: str = Field(default="", alias="PAYMENT_PROVIDER_TOKEN")
    
    # Database
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(..., alias="DB_NAME")
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    
    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    # Channels
    telegram_channel_id: str = Field(..., alias="TELEGRAM_CHANNEL_ID")
    scraped_deals_channel_id: str = Field(default="", alias="SCRAPED_DEALS_CHANNEL_ID")
    admin_cars_channel_id: str = Field(default="", alias="ADMIN_CARS_CHANNEL_ID")
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
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection string"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def database_url_sync(self) -> str:
        """PostgreSQL connection string (Sync)"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Redis connection string"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def admin_list(self) -> List[int]:
        """Parse admin IDs from comma-separated string"""
        return [int(admin_id.strip()) for admin_id in self.admin_ids.split(",")]


# Global settings instance
settings = Settings()
