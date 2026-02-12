"""
Scraper manager to coordinate all scrapers
"""
import json
from datetime import datetime
from typing import List, Dict
from loguru import logger

from scrapers.olx_scraper import OLXScraper
from scrapers.avtoelon_scraper import AvtoelonScraper
from database.database import async_session_maker
from database.crud import create_scraped_listing


class ScraperManager:
    """Manages all scrapers and coordinates scraping tasks"""
    
    def __init__(self):
        self.scrapers = {
            'olx': OLXScraper(headless=True),
            'avtoelon': AvtoelonScraper(headless=True),
        }
    
    async def scrape_all(self, max_pages: int = 3) -> Dict[str, int]:
        """
        Run all scrapers and save results
        
        Args:
            max_pages: Maximum pages to scrape per site
            
        Returns:
            Dictionary with scraping statistics
        """
        stats = {'olx': 0, 'avtoelon': 0, 'new_listings': 0, 'total': 0}
        
        for source, scraper in self.scrapers.items():
            try:
                logger.info(f"Starting {source} scraper...")
                listings = await scraper.scrape_listings(max_pages=max_pages)
                stats[source] = len(listings)
                stats['total'] += len(listings)
                
                # Save to database
                new_count = await self.save_listings(listings, source)
                stats['new_listings'] += new_count
                
                logger.info(f"{source}: {len(listings)} listings scraped, {new_count} new")
                
            except Exception as e:
                logger.error(f"Error scraping {source}: {e}")
        
        return stats
    
    async def save_listings(self, listings: List[Dict], source: str) -> int:
        """
        Save scraped listings to database
        
        Args:
            listings: List of listing dictionaries
            source: Source name ('olx' or 'avtoelon')
            
        Returns:
            Number of new listings saved
        """
        new_count = 0
        
        async with async_session_maker() as session:
            for listing in listings:
                try:
                    # Skip if already exists
                    external_id = f"{source}_{listing.get('external_id', '')}"
                    
                    from database.crud import check_listing_status, get_average_market_price, get_active_competitors_count, find_similar_listing
                    from utils.notifications import publish_scraped_deal
                    
                    # Check existence and price drop
                    status = await check_listing_status(session, external_id, listing.get('price', 0))
                    
                    if status['exists']:
                        if status.get('price_changed') and status.get('change_type') == 'dropped':
                            # Price dropped! Notify
                            logger.info(f"📉 Price Drop: {listing['title']}")
                            
                            # Re-calculate market analysis
                            avg_price = 0
                            if listing.get('brand') and listing.get('model') and listing.get('year'):
                                    avg_price = await get_average_market_price(
                                        session, 
                                        listing['brand'], 
                                        listing['model'], 
                                        listing['year'],
                                        transmission=listing.get('transmission'),
                                        mileage=listing.get('mileage'),
                                        description=listing.get('description')
                                    )                          
                            # Add drop info
                            listing['avg_price'] = avg_price
                            # Is it good deal NOW?
                            listing['is_good_deal'] = (avg_price > 0 and listing['price'] < avg_price * 0.85)
                            
                            # Price drop specifics
                            listing['is_price_drop'] = True
                            listing['old_price'] = status['old_price']
                            listing['price_diff'] = status['diff']
                            
                            # Notify
                            await publish_scraped_deal(listing)
                            
                        continue
                    
                    # New listing logic below
                    # Calculate market analysis
                    avg_price = 0
                    is_good_deal = False
                    
                    if listing.get('brand') and listing.get('model') and listing.get('year'):
                        avg_price = await get_average_market_price(
                            session, 
                            listing['brand'], 
                            listing['model'], 
                            listing['year'],
                            transmission=listing.get('transmission'),
                            mileage=listing.get('mileage'),
                            description=listing.get('description')
                        )
                        
                        if avg_price > 0 and listing.get('price', 0) > 0:
                            # If price is 15% cheaper than market average
                            if listing['price'] < (avg_price * 0.85):
                                is_good_deal = True
                                logger.info(f"🔥 Good deal found: {listing['title']} (${listing['price']} vs avg ${avg_price:.0f})")
                    
                    # Create new listing with all fields
                    listing_obj = await create_scraped_listing(
                        session,
                        source=source,
                        external_id=external_id,
                        url=listing['url'],
                        title=listing['title'],
                        brand=listing.get('brand'),
                        model=listing.get('model'),
                        year=listing.get('year'),
                        price=listing.get('price', 0),
                        mileage=listing.get('mileage'),
                        description=listing.get('description'),
                        location=listing.get('location'),
                        color=listing.get('color'),
                        transmission=listing.get('transmission'),
                        fuel_type=listing.get('fuel_type'),
                        images=listing.get('images', {}),
                        is_good_deal=is_good_deal
                    )
                    
                    
                    # Notify channel about new deal
                    from utils.notifications import publish_scraped_deal, notify_admin_about_good_deal
                    
                    # Enrich listing data with market info for notification
                    listing['avg_price'] = avg_price
                    listing['is_good_deal'] = is_good_deal
                    if listing.get('brand') and listing.get('model') and listing.get('year'):
                        listing['competitor_count'] = await get_active_competitors_count(
                            session, 
                            listing['brand'], 
                            listing['model'], 
                            listing['year'],
                            listing['price']
                        )
                    else:
                        listing['competitor_count'] = 0
                    
                    # Cross-platform check
                    similar = await find_similar_listing(
                        session, 
                        listing.get('brand', ''), 
                        listing.get('model', ''), 
                        listing.get('year', 0), 
                        listing.get('price', 0), 
                        source
                    )
                    if similar:
                        listing['cross_platform_url'] = similar.url
                        listing['cross_platform_source'] = similar.source

                    # Deal Score Calculation
                    score = 50
                    if is_good_deal: score += 15
                    if avg_price > 0 and listing.get('price', 0) < avg_price * 0.8: score += 15 # Super cheap
                    if listing.get('mileage', 100000) < 20000: score += 10
                    
                    desc_lower = (listing.get('description') or "").lower()
                    if 'srochno' in desc_lower: score += 10
                    if 'naqd' in desc_lower: score += 5
                    if 'kraska bor' in desc_lower or 'dtp' in desc_lower or 'udar' in desc_lower: score -= 25
                    
                    listing['deal_score'] = min(100, max(0, score))

                    # Smart Notification Logic
                    location = listing.get('location', '').lower()
                    is_nearby = any(x in location for x in ['toshkent', 'tashkent', 'chirchiq', 'yangiyo', 'kibray', 'zangiota', 'sergeli', 'bektemir', 'chilonzor', 'yunusobod', 'mirzo ulug', 'yakkasaroy', 'shayxontohur', 'olmazor', 'uchtepa', 'sharif'])
                    
                    # 1. Tashkent & Nearby: Notify all (high priority area)
                    # 2. Other regions: Notify ONLY if it's a Good Deal (worth traveling)
                    if is_nearby or is_good_deal:
                        await publish_scraped_deal(listing)
                    
                    if is_good_deal:
                        await notify_admin_about_good_deal(listing)
                    
                    new_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving listing: {e}")
                    continue
        
        return new_count
    
    async def export_to_json(self, listings: List[Dict], filename: str):
        """
        Export listings to JSON file
        
        Args:
            listings: List of listing dictionaries
            filename: Output filename
        """
        try:
            output = {
                'timestamp': datetime.utcnow().isoformat(),
                'count': len(listings),
                'listings': listings
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(listings)} listings to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")


async def run_scraper_task():
    """Celery task to run scrapers periodically"""
    manager = ScraperManager()
    stats = await manager.scrape_all(max_pages=1)
    logger.info(f"Scraping completed: {stats}")
    return stats
