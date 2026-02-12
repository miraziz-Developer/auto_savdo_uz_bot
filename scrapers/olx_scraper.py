"""
OLX.uz scraper for car listings
"""
import re
from typing import List, Dict, Optional
import random
from loguru import logger
from scrapers.base_scraper import BaseScraper


class OLXScraper(BaseScraper):
    """Scraper for OLX.uz car listings"""
    
    BASE_URL = "https://www.olx.uz/transport/legkovye-avtomobili/"
    TARGET_URLS = [
        "https://www.olx.uz/transport/legkovye-avtomobili/chevrolet/gentra/",
        "https://www.olx.uz/transport/legkovye-avtomobili/chevrolet/cobalt/",
        "https://www.olx.uz/transport/legkovye-avtomobili/chevrolet/malibu/",
        "https://www.olx.uz/transport/legkovye-avtomobili/chevrolet/tracker/",
        "https://www.olx.uz/transport/legkovye-avtomobili/kia/",
        "https://www.olx.uz/transport/legkovye-avtomobili/?search%5Border%5D=created_at:desc"  # General recent
    ]
    
    async def scrape_listings(self, max_pages: int = 1) -> List[Dict]:
        """
        Scrape car listings from OLX.uz
        
        Args:
            max_pages: Maximum number of pages to scrape PER URL
            
        Returns:
            List of parsed listings
        """
        await self.init_browser()
        listings = []
        
        try:
            # Shuffle URLs to avoid pattern detection
            urls = self.TARGET_URLS.copy()
            random.shuffle(urls)
            
            for base_url in urls:
                for page_num in range(1, max_pages + 1):
                    url = f"{base_url}?page={page_num}" if '?' not in base_url else f"{base_url}&page={page_num}"
                    logger.info(f"Scraping OLX: {url}")
                    
                    try:
                        await self.goto_with_retry(url)
                        await self.page.wait_for_timeout(2000)  # Wait for dynamic content
                        
                        # Get all listing cards
                        listing_elements = await self.page.query_selector_all('[data-cy="l-card"]')
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
                        await self.page.wait_for_timeout(2000 + int(1000 * (0.5 - random.random())))
                        
                    except Exception as e:
                        logger.error(f"Error scraping URL {url}: {e}")
                        continue
        
        finally:
            await self.close_browser()
        
        logger.info(f"Total listings scraped from OLX: {len(listings)}")
        return listings
    
    async def parse_listing(self, element) -> Optional[Dict]:
        """
        Parse individual OLX listing
        
        Args:
            element: Playwright element handle
            
        Returns:
            Parsed listing data or None
        """
        try:
            # Get link and ID
            link_element = await element.query_selector('a[href*="/d/"]')
            if not link_element:
                return None
            
            url = await link_element.get_attribute('href')
            if not url.startswith('http'):
                url = f"https://www.olx.uz{url}"
            
            # Extract ID from URL
            external_id = url.split('/d/')[1].split('/')[0] if '/d/' in url else None
            
            # Get title
            title_element = await element.query_selector('h6')
            title = await title_element.inner_text() if title_element else ""
            
            # Get price
            price_element = await element.query_selector('[data-testid="ad-price"]')
            price_text = await price_element.inner_text() if price_element else "0"
            
            # Parse price (remove spaces and "so'm")
            price = self.parse_price(price_text)
            
            # Get image
            img_element = await element.query_selector('img')
            image_url = await img_element.get_attribute('src') if img_element else None
            
            # Extract brand, model, year from title
            brand, model, year = self.extract_car_info(title)
            
            # Get location and date
            location_element = await element.query_selector('[data-testid="location-date"]')
            location_date = await location_element.inner_text() if location_element else ""
            
            # Extract basic details from visible text
            # OLX cards often have text like "Sedan • 2022 • 45 000 km • Benzin"
            all_text = await element.inner_text()
            
            mileage = 0
            mileage_match = re.search(r'(\d+[\d\s]*)\s*km', all_text)
            if mileage_match:
                mileage = int(re.sub(r'[^\d]', '', mileage_match.group(1)))
                
            fuel_type = "Noma'lum"
            if "Benzin" in all_text: fuel_type = "Benzin"
            elif "Gaz" in all_text: fuel_type = "Gaz"
            elif "Dizel" in all_text: fuel_type = "Dizel"
            elif "Elektr" in all_text: fuel_type = "Elektr"
            elif "Gibrid" in all_text: fuel_type = "Gibrid"
            
            transmission = "Noma'lum"
            if "Avtomat" in all_text: transmission = "Avtomat"
            elif "Mexanika" in all_text: transmission = "Mexanika"

            return {
                'source': 'olx',
                'external_id': external_id,
                'url': url,
                'title': title.strip(),
                'brand': brand,
                'model': model,
                'year': year,
                'price': price,
                'mileage': mileage,
                'location': location_date,
                'fuel_type': fuel_type,
                'transmission': transmission,
                'description': "", # Detailed description requires opening the page
                'images': {'main': image_url} if image_url else None,
            }
        
        except Exception as e:
            logger.error(f"Error parsing OLX listing: {e}")
            return None
    
    @staticmethod
    def parse_price(price_text: str) -> float:
        """Parse price from text in USD"""
        try:
            # Remove all non-digit characters except decimal point
            price_clean = re.sub(r'[^\d.]', '', price_text.replace(' ', '').replace(',', ''))
            if not price_clean:
                return 0.0
                
            val = float(price_clean)
            
            # If "y.e" or "$" is NOT in text, it's likely UZS - convert to USD
            if 'y.e' not in price_text.lower() and '$' not in price_text:
                return round(val / 12800, 2) # UZS to USD
            
            return val # Already USD
        except:
            return 0.0
    
    @staticmethod
    def extract_car_info(title: str) -> tuple:
        """
        Extract brand, model, and year from title
        
        Returns:
            (brand, model, year) tuple
        """
        title_lower = title.lower()
        
        # Comprehensive list of brands in Uzbekistan
        brands = {
            'chevrolet': ['gentra', 'lacetti', 'malibu', 'spark', 'nexia', 'cobalt', 'captiva', 'tahoe', 'monza', 'onix', 'tracker', 'equinox', 'damas', 'labo'],
            'daewoo': ['nexia', 'matiz', 'tico', 'damas', 'gentra'],
            'byd': ['song', 'han', 'tang', 'seagull', 'dolphin', 'chazor', 'destroyer', 'e2', 'qin'],
            'chery': ['tiggo 7', 'tiggo 8', 'tiggo 4', 'arrizo', 'tiggo'],
            'jetour': ['x70', 'x90', 'dashing', 'traveller'],
            'lada': ['vesta', 'granta', 'niva', 'largus', 'xray', 'priora', 'kalina', '2107', '2106'],
            'hyundai': ['accent', 'sonata', 'elantra', 'santa fe', 'tucson', 'palisade', 'staria', 'creta', 'kusta'],
            'kia': ['rio', 'cerato', 'sportage', 'sorento', 'k5', 'k8', 'k9', 'seltos', 'carnival', 'ev6'],
            'toyota': ['camry', 'corolla', 'land cruiser', 'prado', 'rav4', 'highlander', 'hilux'],
            'mercedes': ['s-class', 'e-class', 'c-class', 'g-class', 'ml', 'gl', 'gle', 'gls', 'w221', 'w222', 'w223'],
            'bmw': ['x5', 'x6', 'x7', '3-series', '5-series', '7-series', 'm5', 'm3'],
            'nissan': ['qashqai', 'x-trail', 'patrol', 'juke', 'altima', 'sentra'],
            'honda': ['accord', 'civic', 'cr-v', 'envix'],
            'mazda': ['3', '6', 'cx-5', 'cx-9'],
            'lexus': ['rx', 'lx', 'es', 'is', 'gx'],
            'volkswagen': ['id.4', 'id.6', 'teramont', 'bora', 'tiguan', 'touareg'],
            'skoda': ['kodiaq', 'octavia', 'superb'],
            'geely': ['monjaro', 'coolray', 'tugella', 'emgrand'],
            'haval': ['jolion', 'h6', 'darzo', 'm6'],
            'gac': ['gs8', 'm8', 'aion'],
        }
        
        brand = "Noma'lum"
        model = "Noma'lum"
        
        # Find brand
        for brand_name in brands.keys():
            if brand_name in title_lower:
                brand = brand_name.capitalize()
                # Find model
                for model_name in brands[brand_name]:
                    if model_name in title_lower:
                        model = model_name.upper()
                        break
                break
        
        # Extract year (4 digits between 1970-2026)
        year_match = re.search(r'\b(19[789]\d|20[012]\d)\b', title)
        year = int(year_match.group(1)) if year_match else None
        
        return brand, model, year

