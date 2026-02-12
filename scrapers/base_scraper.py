"""
Base scraper class with common functionality
"""
import random
import playwright.async_api
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from playwright_stealth import Stealth
from loguru import logger


class BaseScraper(ABC):
    """Base class for web scrapers"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright_instance = None
    
    def get_random_user_agent(self) -> str:
        """Get random user agent"""
        return random.choice(self.USER_AGENTS)
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        # Using full module path to avoid naming collisions
        self.playwright_instance = await playwright.async_api.async_playwright().start()
        
        self.browser = await self.playwright_instance.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(user_agent=self.get_random_user_agent())
        self.page = await self.context.new_page()
        
        # Apply stealth using the Stealth class
        stealth_config = Stealth()
        await stealth_config.apply_stealth_async(self.page)
        
        logger.info("Browser initialized")
    
    async def close_browser(self):
        """Close browser"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright_instance:
                await self.playwright_instance.stop()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        logger.info("Browser closed")
    
    async def goto_with_retry(self, url: str, max_retries: int = 3):
        """Navigate to URL with retry logic"""
        for attempt in range(max_retries):
            try:
                await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
                return
            except Exception as e:
                if attempt == max_retries - 1: raise e
                await self.page.wait_for_timeout(2000)
    
    @abstractmethod
    async def scrape_listings(self) -> List[Dict]: pass
    
    @abstractmethod
    def parse_listing(self, element) -> Optional[Dict]: pass
