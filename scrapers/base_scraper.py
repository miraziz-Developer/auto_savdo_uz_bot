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
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
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
                await self.random_sleep(2, 5) # Smart delay after navigation
                return
            except Exception as e:
                logger.warning(f"Navigation error (attempt {attempt+1}): {e}")
                if attempt == max_retries - 1: raise e
                await self.random_sleep(5, 10)

    async def random_sleep(self, min_seconds: float = 3.0, max_seconds: float = 7.0):
        """Random sleep to mimic human behavior"""
        import asyncio
        delay = random.uniform(min_seconds, max_seconds)
        # logger.debug(f"Sleeping for {delay:.2f} seconds...")
        await asyncio.sleep(delay)
    
    @abstractmethod
    async def scrape_listings(self) -> List[Dict]: pass
    
    @abstractmethod
    def parse_listing(self, element) -> Optional[Dict]: pass
