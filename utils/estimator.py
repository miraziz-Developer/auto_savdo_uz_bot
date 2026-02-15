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
    
    # Taxminiy yangi narxlar (O'zbekiston bozor, USD)
    BASE_NEW_PRICES = {
        'gentra': 16000, 'lacetti': 15000,
        'cobalt': 14000, 'nexia 3': 12000, 'nexia': 10000,
        'spark': 11000, 'matiz': 6000, 'damas': 9500,
        'malibu': 35000, 'tracker': 22000, 'equinox': 38000,
        'captiva': 30000, 'tahoe': 85000, 'traverse': 60000, 'onix': 17000,
        'monza': 18000,
        # Hyundai
        'accent': 18000, 'elantra': 25000, 'sonata': 35000,
        'tucson': 38000, 'santa fe': 45000, 'palisade': 65000,
        # Kia
        'rio': 19000, 'cerato': 26000, 'k5': 36000, 'k8': 45000,
        'seltos': 28000, 'sportage': 40000, 'sorento': 50000, 'carnival': 55000,
        # BYD
        'chazor': 22000, 'song plus': 32000, 'han': 55000, 'tang': 60000,
        # Toyota
        'corolla': 25000, 'camry': 40000, 'prado': 70000, 'land cruiser': 100000,
        # Lada
        'vesta': 15000, 'granta': 11000, 'niva': 12000,
    }

    @classmethod
    def estimate_price(cls, brand: str, model: str, year: int, mileage: int = 0, condition: str = "good") -> Dict[str, float]:
        """
        Moshina narxini hisoblash (nazariy)
        """
        # Find base price for model
        model_key = model.lower().strip()
        price_new = cls.BASE_NEW_PRICES.get(model_key)
        
        # Fuzzy / partial match backup
        if not price_new:
            for k, v in cls.BASE_NEW_PRICES.items():
                if k in model_key or model_key in k:
                    price_new = v
                    break
        
        # Default fallback
        if not price_new:
            price_new = 20000  # Generic average car
            
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # 1. Base Depreciation
        rate = cls.DEPRECIATION_RATES.get(brand, cls.DEPRECIATION_RATES['Other'])
        
        # Narx formulasi: P = P0 * (1 - r)^t
        estimated = price_new * ((1 - rate) ** age)
        
        # 2. Mileage Adjustment
        if mileage > 0:
            avg_mileage = age * 15000  # Yiliga o'rtacha 15k km
            diff = mileage - avg_mileage
            estimated -= (estimated * (diff * cls.MILEAGE_FACTOR / 100))
        elif mileage is None or mileage == 0:
             # Assume average mileage if not provided
             pass
                
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
