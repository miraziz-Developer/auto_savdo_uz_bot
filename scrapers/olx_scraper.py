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
        """
        await self.init_browser()
        listings = []
        
        try:
            # Shuffle URLs to avoid pattern detection
            urls = self.TARGET_URLS.copy()
            random.shuffle(urls)
            
            for base_url in urls:
                # Randomize number of pages to behave human-like (1-2 pages)
                pages_to_scrape = min(max_pages, random.randint(1, 2))
                
                for page_num in range(1, pages_to_scrape + 1):
                    list_url = f"{base_url}?page={page_num}" if '?' not in base_url else f"{base_url}&page={page_num}"
                    logger.info(f"Scraping OLX List: {list_url}")
                    
                    try:
                        await self.goto_with_retry(list_url)
                        
                        # Collect all URLs from the list page first
                        listing_urls = await self.get_card_urls()
                        logger.info(f"Found {len(listing_urls)} listings on {list_url}")
                        
                        # Visit each listing URL directly for better data
                        # Only take random subset per run to avoid heavy load
                        random.shuffle(listing_urls)
                        target_listings = listing_urls[:5] # Limit per page per run
                        
                        for url in target_listings:
                            try:
                                data = await self.scrape_listing_details(url)
                                if data:
                                    listings.append(data)
                                    # Short delay between listings
                                    await self.random_sleep(3, 8)
                            except Exception as e:
                                logger.error(f"Error scraping listing {url}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error processing list page {list_url}: {e}")
                        continue
                        
                    # Delay between pages
                    await self.random_sleep(5, 10)
        
        finally:
            await self.close_browser()
        
        logger.info(f"Total listings scraped from OLX: {len(listings)}")
        return listings

    async def get_card_urls(self) -> List[str]:
        """Extract URLs from the list view cards"""
        urls = []
        try:
            # Select all card links
            elements = await self.page.query_selector_all('[data-cy="l-card"] a[href*="/d/"]')
            for el in elements:
                href = await el.get_attribute('href')
                if href:
                    full_url = f"https://www.olx.uz{href}" if not href.startswith('http') else href
                    urls.append(full_url)
        except Exception as e:
            logger.error(f"Error extracting URLs: {e}")
        return list(set(urls))  # Deduplicate

    async def scrape_listing_details(self, url: str) -> Optional[Dict]:
        """
        Visit the detailed listing page and extract distinct attributes
        """
        try:
            from utils.currency import get_usd_rate
            current_rate = await get_usd_rate()
            
            logger.info(f"Scraping details: {url}")
            await self.goto_with_retry(url)
            await self.page.wait_for_timeout(1000) # Wait for render
            
            # Extract distinct ID from URL
            external_id = None
            if '-ID' in url:
                match = re.search(r'-ID(\w+)\.html', url)
                if match:
                    external_id = match.group(1)
            
            # Title
            title_el = await self.page.query_selector('h1, h4, [data-cy="ad_title"]')
            title = await title_el.inner_text() if title_el else ""
            
            # Price
            try:
                price_el = await self.page.query_selector('[data-testid="ad-price-container"] h3, [data-testid="ad-price-container"] h2, h3[class*="css-"], h2[class*="css-"]') 
                price_text = await price_el.inner_text() if price_el else ""
                
                if not price_text:
                    # Backup: search the page for anything that looks like price
                    all_h3s = await self.page.query_selector_all('h2, h3')
                    for h3 in all_h3s:
                        text = await h3.inner_text()
                        if 'y.e.' in text.lower() or '$' in text or "so'm" in text.lower() or 'sum' in text.lower():
                            price_text = text
                            break
                            
                price = self.parse_price(price_text, current_rate)
            except Exception as e:
                logger.error(f"❌ Failed to extract price: {e}")
                from utils.notifications import notify_admin_about_error
                await notify_admin_about_error(f"OLX Price Scraping Failed for {url}: {e}")
                price = 0
            
            # Location and Date (often in a specific span)
            location = "Toshkent" # Default
            # Try to find location text
            loc_el = await self.page.query_selector('[data-testid="main"] span[class*="css-"]') 
            # This selector is weak, better to grab full text and regex
            
            # Grab all parameter text
            # Usually stored in a list
            params_text = ""
            param_list = await self.page.query_selector_all('li p') # Common OLX param structure
            for p in param_list:
                params_text += (await p.inner_text()) + "\n"
            
            # Backup: get all body text
            body_text = await self.page.inner_text('body')
            
            # Extract Attributes using Regex (supporting RU and UZ)
            # Mileage
            mileage = 0
            mileage_match = re.search(r'(Пробег|Yurgani)[:\s]+(\d+[\d\s]*)\s*km', body_text, re.IGNORECASE)
            if mileage_match:
                mileage = int(re.sub(r'[^\d]', '', mileage_match.group(2)))
            
            # Year
            year = None
            year_match = re.search(r'(Год выпуска|Ishlab chiqarilgan yili)[:\s]+(\d{4})', body_text, re.IGNORECASE)
            if year_match:
                year = int(year_match.group(2))
            
            # Fuel
            fuel_type = "Noma'lum"
            if re.search(r'(Бензин|Benzin)', body_text, re.IGNORECASE): fuel_type = "Benzin"
            elif re.search(r'(Газ|Gaz)', body_text, re.IGNORECASE): fuel_type = "Gaz"
            elif re.search(r'(Дизель|Dizel)', body_text, re.IGNORECASE): fuel_type = "Dizel"
            elif re.search(r'(Электро|Elektr)', body_text, re.IGNORECASE): fuel_type = "Elektr"
            elif re.search(r'(Гибрид|Gibrid)', body_text, re.IGNORECASE): fuel_type = "Gibrid"
            
            # Transmission
            transmission = "Noma'lum"
            if re.search(r'(Автомат|Avtomat)', body_text, re.IGNORECASE): transmission = "Avtomat"
            elif re.search(r'(Механи|Mexani)', body_text, re.IGNORECASE): transmission = "Mexanika"
            
            # Brand/Model extraction - try from title first, or params
            brand, model, scraped_year = self.extract_car_info(title + " " + body_text)
            if year is None and scraped_year:
                year = scraped_year
            
            # Images
            image_url = None
            img_el = await self.page.query_selector('.swiper-slide-active img')
            if not img_el:
                img_el = await self.page.query_selector('img[src*="olxcdn.com"]')
            
            if img_el:
                image_url = await img_el.get_attribute('src')

            # Fallback for Location
            # Often appearing as "Ташкент, Мирзо-Улугбекский район"
            # We preserve navigation text or footer text
            
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
                'location': "Toshkent", # Placeholder, hard to reliably extract dynamic loc
                'fuel_type': fuel_type,
                'transmission': transmission,
                'description': f"{title}\n{body_text[:3000]}",
                'images': {'main': image_url} if image_url else None,
            }

        except Exception as e:
            logger.error(f"Detailed parsing failed for {url}: {e}")
            return None

    @staticmethod
    def parse_price(price_text: str, current_rate: float = 12900.0) -> float:
        """Parse price from text in USD using dynamic rate"""
        try:
            # Remove all non-digit characters except decimal point
            # Detect currency
            is_uzs = "sum" in price_text.lower() or "so'm" in price_text.lower()
            
            price_clean = re.sub(r'[^\d.]', '', price_text.replace(' ', '').replace(',', ''))
            if not price_clean:
                return 0.0
                
            val = float(price_clean)
            
            if is_uzs and current_rate > 0:
                return round(val / current_rate, 0)
            
            return val
        except:
            return 0.0
    
    @staticmethod
    def extract_car_info(text: str) -> tuple:
        """
        Extract brand, model, and year from text blob
        """
        text_lower = text.lower()
        
        brands = {
            'chevrolet': ['gentra', 'lacetti', 'malibu', 'spark', 'nexia', 'cobalt', 'captiva', 'tahoe', 'monza', 'onix', 'tracker', 'equinox', 'damas', 'labo'],
            'daewoo': ['nexia', 'matiz', 'tico', 'damas', 'gentra'],
            'kia': ['k5', 'k8', 'carnival', 'sorento', 'sportage', 'seltos', 'sonet', 'stinger', 'cerato', 'rio', 'ev6', 'ev9'],
            'hyundai': ['elantra', 'sonata', 'tucson', 'santa fe', 'palisade', 'creta', 'accent', 'staria'],
            'byd': ['song', 'han', 'tang', 'chazor', 'destroyer', 'seagull', 'dolphin', 'e2', 'qin'],
            'toyota': ['camry', 'prado', 'land cruiser', 'corolla', 'cross', 'rav4', 'highlander'],
            'lada': ['vesta', 'xray', 'largus', 'niva', 'granta', 'priora'],
            'chery': ['tiggo', 'arrizo'],
            'jetour': ['x70', 'x90', 'dashing', 'traveller'],
            'geely': ['monjaro', 'coolray', 'tugella', 'emgrand'],
            'bmw': ['x5', 'x6', 'x7', '5-series', '7-series', 'm5'],
            'mercedes': ['s-class', 'e-class', 'c-class', 'g-class', 'cls', 'gle', 'gls'],
            'zeekr': ['001', '007', 'x', '009'],
            'li': ['l7', 'l9', 'l6', 'one'],
        }
        
        brand = "Noma'lum"
        model = "Noma'lum"
        
        # Heuristic: First match wins
        for b_name, m_list in brands.items():
            if b_name in text_lower:
                brand = b_name.capitalize()
                for m in m_list:
                    if m in text_lower:
                        model = m.upper()
                        break
                break
        
        # If brand not found but model is unique (e.g. "Gentra")
        if brand == "Noma'lum":
            for b_name, m_list in brands.items():
                for m in m_list:
                    if m in text_lower:
                        brand = b_name.capitalize()
                        model = m.upper()
                        break
                if brand != "Noma'lum": break

        # Year
        year = None
        # Look for explicit year patterns
        # 1. "2023 yil"
        # 2. "2023 г"
        # 3. just "2023" isolated
        year_matches = re.findall(r'\b(199\d|20[012]\d)\b', text)
        if year_matches:
            # Take the max year found usually (listing year is likely the car year)
            # But filter reasonable scraping date vs car date
            valid_years = [int(y) for y in year_matches if 1990 <= int(y) <= 2026]
            if valid_years:
                year = max(valid_years)
        
        return brand, model, year

    def parse_listing(self, element) -> Optional[Dict]:
        """
        Abstract method implementation (unused in new navigation logic)
        """
        return None
