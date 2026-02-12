"""
Script to run scrapers manually
"""
import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.olx_scraper import OLXScraper
from scrapers.avtoelon_scraper import AvtoelonScraper
from scrapers.scraper_manager import ScraperManager
from loguru import logger


async def run_olx_only():
    """Run only OLX scraper"""
    logger.info("Running OLX scraper...")
    scraper = OLXScraper(headless=False)  # Set to False to see browser
    listings = await scraper.scrape_listings(max_pages=2)
    
    # Save to JSON
    output = {
        'source': 'olx',
        'count': len(listings),
        'listings': listings
    }
    
    with open('olx_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(listings)} listings to olx_results.json")


async def run_avtoelon_only():
    """Run only Avtoelon scraper"""
    logger.info("Running Avtoelon scraper...")
    scraper = AvtoelonScraper(headless=False)
    listings = await scraper.scrape_listings(max_pages=2)
    
    # Save to JSON
    output = {
        'source': 'avtoelon',
        'count': len(listings),
        'listings': listings
    }
    
    with open('avtoelon_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(listings)} listings to avtoelon_results.json")


async def run_all_scrapers():
    """Run all scrapers"""
    logger.info("Running all scrapers...")
    manager = ScraperManager()
    stats = await manager.scrape_all(max_pages=2)
    
    logger.info(f"Scraping completed: {stats}")


if __name__ == "__main__":
    print("""
🔍 Scraper Test Script

Quyidagi variantlardan birini tanlang:
1. Faqat OLX
2. Faqat Avtoelon
3. Hammasi (to'liq test)

Tanlang (1-3): """, end='')
    
    choice = input().strip()
    
    if choice == '1':
        asyncio.run(run_olx_only())
    elif choice == '2':
        asyncio.run(run_avtoelon_only())
    elif choice == '3':
        asyncio.run(run_all_scrapers())
    else:
        print("❌ Noto'g'ri tanlov")
