"""
Currency Utility — Valyuta kurslarini boshqarish
Markaziy Bank API orqali dollar kursini oladi va keshlaydi.
"""
import aiohttp
import json
import asyncio
from datetime import datetime, timedelta
from loguru import logger

# Kesh uchun global o'zgaruvchilar
_CACHED_RATE = 12900.0  # Fallback rate (agar API ishlamasa)
_LAST_UPDATED = None
_CACHE_TTL = timedelta(hours=12)  # 12 soat davomida kursni saqlash

async def get_usd_rate() -> float:
    """
    Markaziy Bankdan USD kursini olish.
    Kesh va xatoliklardan himoya mavjud.
    """
    global _CACHED_RATE, _LAST_UPDATED
    
    now = datetime.utcnow()
    
    # Agar kesh yangi bo'lsa, uni qaytarish
    if _LAST_UPDATED and (now - _LAST_UPDATED) < _CACHE_TTL:
        return _CACHED_RATE
        
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # 5 sec max
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # CBU API (Markaziy Bank)
            async with session.get('https://cbu.uz/oz/arkhiv-kursov-valyut/json/') as response:
                if response.status == 200:
                    data = await response.json()
                    # USD ni topish
                    for currency in data:
                        if currency['Ccy'] == 'USD':
                            rate = float(currency['Rate'])
                            _CACHED_RATE = rate
                            _LAST_UPDATED = now
                            logger.info(f"🔄 Valyuta kursi yangilandi: 1 USD = {_CACHED_RATE} UZS")
                            return _CACHED_RATE
    except Exception as e:
        logger.error(f"⚠️ Valyuta kursini olishda xatolik: {e}")
        # Xatolik bo'lsa, eski keshni yoki fallback kursni qaytaradi
    
    return _CACHED_RATE

def convert_uzs_to_usd(amount_uzs: float, rate: float = None) -> float:
    """So'mni dollarga o'girish"""
    current_rate = rate or _CACHED_RATE
    if current_rate <= 0: return 0.0
    return round(amount_uzs / current_rate, 0)

def convert_usd_to_uzs(amount_usd: float, rate: float = None) -> float:
    """Dollarni so'mga o'girish"""
    current_rate = rate or _CACHED_RATE
    return round(amount_usd * current_rate, 0)
