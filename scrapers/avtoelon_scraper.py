"""
Avtoelon.uz scraper for car listings
"""
import re
import random
from typing import List, Dict, Optional
from loguru import logger
from scrapers.base_scraper import BaseScraper


class AvtoelonScraper(BaseScraper):
    """Scraper for Avtoelon.uz car listings"""
    
    BASE_URL = "https://avtoelon.uz/avto"
    
    async def scrape_listings(self, max_pages: int = 3) -> List[Dict]:
        """
        Scrape car listings from Avtoelon.uz
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of parsed listings
        """
        await self.init_browser()
        listings = []
        
        try:
            for page_num in range(1, max_pages + 1):
                url = f"{self.BASE_URL}?page={page_num}"
                logger.info(f"Scraping Avtoelon page {page_num}: {url}")
                
                await self.goto_with_retry(url)
                await self.page.wait_for_timeout(2000)
                
                # Get all listing cards
                listing_elements = await self.page.query_selector_all('.list-item.a-elem')
                logger.info(f"Found {len(listing_elements)} listings on page {page_num}")
                
                for element in listing_elements:
                    try:
                        listing_data = await self.parse_listing(element)
                        if listing_data:
                            listings.append(listing_data)
                    except Exception as e:
                        logger.error(f"Error parsing listing: {e}")
                        continue
                
                # Random delay between pages
                await self.page.wait_for_timeout(3000 + int(2000 * (0.5 - random.random())))
        
        finally:
            await self.close_browser()
        
        logger.info(f"Total listings scraped from Avtoelon: {len(listings)}")
        return listings
    
    async def parse_listing(self, element) -> Optional[Dict]:
        """
        Parse individual Avtoelon listing
        
        Args:
            element: Playwright element handle
            
        Returns:
            Parsed listing data or None
        """
        try:
            # Get link and ID
            link_element = await element.query_selector('.js__advert-link')
            if not link_element:
                return None
            
            url = await link_element.get_attribute('href')
            if not url.startswith('http'):
                url = f"https://avtoelon.uz{url}"
            
            # Extract ID from URL
            external_id = url.split('/')[-1] if '/' in url else None
            
            # Get title
            title_element = await element.query_selector('.js__advert-link')
            title = await title_element.inner_text() if title_element else ""
            
            # Get price
            price_element = await element.query_selector('.price')
            price_text = await price_element.inner_text() if price_element else "0"
            
            price = self.parse_price(price_text)
            
            # Get year
            year_element = await element.query_selector('.year')
            year_text = await year_element.inner_text() if year_element else ""
            year = self.parse_year(year_text)
            
            # Get image
            img_element = await element.query_selector('.a-elem__image')
            image_url = await img_element.get_attribute('src') if img_element else None
            if image_url and not image_url.startswith('http'):
                image_url = f"https://avtoelon.uz{image_url}"
            
            # Extract brand and model from title
            brand, model = self.extract_brand_model(title)
            
            # Parse description params to get details
            params_text = await element.inner_text()
            
            # Mileage
            mileage = 0
            mileage_match = re.search(r'(\d+[\d\s]*)\s*km', params_text)
            if mileage_match:
                mileage = int(re.sub(r'[^\d]', '', mileage_match.group(1)))
                
            # Transmission
            transmission = "Noma'lum"
            if "Avtomat" in params_text or "Automatic" in params_text: transmission = "Avtomat"
            elif "Mexanika" in params_text or "Manual" in params_text: transmission = "Mexanika"
            
            # Fuel
            fuel_type = "Noma'lum"
            if "Benzin" in params_text: fuel_type = "Benzin"
            elif "Gaz" in params_text: fuel_type = "Gaz"
            elif "Dizel" in params_text: fuel_type = "Dizel"
            elif "Elektr" in params_text: fuel_type = "Elektr"
            
            # Location
            location = "Toshkent" # Default as Avtoelon often implies Tashkent, but can be improved
            if "Toshkent" in params_text: location = "Toshkent"
            elif "Samarqand" in params_text: location = "Samarqand"
            elif "Andijon" in params_text: location = "Andijon"

            return {
                'source': 'avtoelon',
                'external_id': external_id,
                'url': url,
                'title': title.strip(),
                'brand': brand,
                'model': model,
                'year': year,
                'price': price,
                'mileage': mileage,
                'location': location,
                'transmission': transmission,
                'fuel_type': fuel_type,
                'color': "Noma'lum", # Hard to extract from list view without specific selector
                'description': "",
                'images': {'main': image_url} if image_url else None,
            }
        
        except Exception as e:
            logger.error(f"Error parsing Avtoelon listing: {e}")
            return None
    
    @staticmethod
    def parse_price(price_text: str) -> float:
        """Parse price from text (Avtoelon is already USD)"""
        try:
            # Remove all non-digit characters
            price_clean = re.sub(r'[^\d]', '', price_text)
            
            if price_clean:
                return float(price_clean)
            
            return 0.0
        except:
            return 0.0
    
    @staticmethod
    def parse_year(year_text: str) -> Optional[int]:
        """Parse year from text"""
        try:
            year_match = re.search(r'\b(19[9]\d|20[0-2]\d)\b', year_text)
            return int(year_match.group(1)) if year_match else None
        except:
            return None
    
    @staticmethod
    def extract_brand_model(title: str) -> tuple:
        """
        Extract brand and model from title
        
        Returns:
            (brand, model) tuple
        """
        title_parts = title.split(',')
        
        if len(title_parts) >= 2:
            brand = title_parts[0].strip()
            model = title_parts[1].strip()
            return brand, model
        elif len(title_parts) == 1:
            # Try to split by space
            words = title.split()
            if len(words) >= 2:
                return words[0], words[1]
        
        return None, None
