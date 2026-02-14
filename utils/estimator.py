"""
Smart Price Estimator — Narxlarni bashorat qilish va tahlil qilish
"""
from datetime import datetime
from typing import Optional, Dict

class PriceEstimator:
    """
    Automated Price Estimation Engine
    Uses depreciation curves and market adjustments
    """
    
    # Yillik amortizatsiya (narx tushishi) foizi
    DEPRECIATION_RATES = {
        'Chevrolet': 0.05,  # 5% (Gentra/Cobalt narxni ushlaydi)
        'Kia': 0.08,
        'Hyundai': 0.08,
        'BYD': 0.10,        # Elektrlar tezroq tushishi mumkin
        'BMW': 0.12,
        'Mercedes': 0.12,
        'Lada': 0.09,
        'Other': 0.10
    }
    
    # Probeg ta'siri (har 1000 km uchun narx tushishi coeff)
    MILEAGE_FACTOR = 0.00005 # 100k km = 5% tushish
    
    @classmethod
    def estimate_price(cls, brand: str, year: int, price_new: float, mileage: int = 0) -> Dict[str, float]:
        """
        Moshina narxini hisoblash (nazariy)
        
        Args:
            brand: Moshina markasi (Chevrolet)
            year: Yili
            price_new: Yangi paytidagi narxi (o'rtacha)
            mileage: Yurgani (km)
            
        Returns:
            Dict: {min, max, recommended}
        """
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # 1. Base Depreciation (Yiliga qarab)
        rate = cls.DEPRECIATION_RATES.get(brand, cls.DEPRECIATION_RATES['Other'])
        
        # Narx formulasi: P = P0 * (1 - r)^t
        estimated = price_new * ((1 - rate) ** age)
        
        # 2. Mileage Adjustment
        if mileage > 0:
            avg_mileage = age * 15000  # Yiliga o'rtacha 15k km
            diff = mileage - avg_mileage
            
            # Agar ko'p yurgan bo'lsa, narx tushadi
            if diff > 0:
                estimated -= (estimated * (diff * cls.MILEAGE_FACTOR / 100))
            # Kam yurgan bo'lsa, narx oshadi (lekin max 10%)
            else:
                estimated += min(estimated * 0.1, abs(diff) * cls.MILEAGE_FACTOR * estimated / 100)
                
        # 3. Market Correction (Uzbekistan Specific)
        # O'zbekistonda GM moshinalari narxi oshishi mumkin (shapka)
        if brand == 'Chevrolet' and age < 3:
            estimated *= 1.05  # +5% bozordagi talab
            
        return {
            "min_price": round(estimated * 0.9, -1),
            "max_price": round(estimated * 1.1, -1),
            "recommended": round(estimated, -1)
        }

    @staticmethod
    def analyze_deal(price: float, market_avg: float) -> str:
        """E'lon qanchalik yaxshi ekanini aniqlash"""
        if market_avg <= 0: return "unknown"
        
        diff_percent = ((market_avg - price) / market_avg) * 100
        
        if diff_percent > 20: return "super_cheap"     # 20% dan arzon
        if diff_percent > 10: return "good_deal"       # 10-20% arzon
        if diff_percent > -5: return "fair_price"      # Normal narx
        if diff_percent > -15: return "slightly_high"  # Biroz qimmat
        return "expensive"                             # Qimmat
