"""
Catalog — Moshinalar katalogi, qidiruv, filtrlar
Foydalanuvchi moshinalarni ko'radi, filtrlaydi, bog'lanadi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from database.database import async_session_maker
from database.crud import get_cars, get_car_by_id, increment_car_views
from keyboards.user_keyboards import car_filters_keyboard, main_menu_keyboard
from states.states import CarSearchStates

router = Router()

# Global comparison storage (in production, use Redis)
comparison_cars = {}

# User favorites and saved searches (in production, use database)
user_favorites = {}
user_saved_searches = {}

# Multi-language support
TRANSLATIONS = {
    'uz': {
        'catalog': '🚗 Katalog',
        'search': '🔍 Qidiruv',
        'favorites': '❤️ Sevimlilar',
        'saved_searches': '🔖 Saqlangan Qidiruvlar',
        'ai_recommendations': '🤖 AI Tavsiyalar',
        'price_prediction': '💰 Narx Bashorati',
        'comparison': '🔄 Solishtirish',
        'main_menu': '🏠 Bosh menyu',
        'back': '◀️ Orqaga',
        'next': 'Keyingisi ▶️',
        'loading': '🔄 Yuklanmoqda...',
        'no_cars': '🔍 So\'rovingiz bo\'yicha moshinalar topilmadi.',
        'error': '❌ Xatolik yuz berdi',
        'total_found': 'Jami {} ta moshina topildi',
        'page': 'Sahifa',
        'price_range': '💰 Narx: {} - {} $',
        'brand_filter': '🏷 Brend: {}',
        'cars_found': '{} ta moshina topildi!',
        'catalog_title': 'MOSHINALAR KATALOGI',
        'quick_filters': 'Tezkor filtrni tanlang yoki 🔍 Qidiruv orqali toping:',
        'all_cars': '📋 Barchasi'
    },
    'ru': {
        'catalog': '🚗 Каталог',
        'search': '🔍 Поиск',
        'favorites': '❤️ Избранное',
        'saved_searches': '🔖 Сохраненные поиски',
        'ai_recommendations': '🤖 AI Рекомендации',
        'price_prediction': '💰 Прогноз цены',
        'comparison': '🔄 Сравнение',
        'main_menu': '🏠 Главное меню',
        'back': '◀️ Назад',
        'next': 'Далее ▶️',
        'loading': '🔄 Загрузка...',
        'no_cars': '🔍 По вашему запросу автомобили не найдены.',
        'error': '❌ Произошла ошибка',
        'total_found': 'Найдено {} автомобилей',
        'page': 'Страница',
        'price_range': '💰 Цена: {} - {} $',
        'brand_filter': '🏷 Бренд: {}',
        'cars_found': 'Найдено {} автомобилей!',
        'catalog_title': 'КАТАЛОГ АВТОМОБИЛЕЙ',
        'quick_filters': 'Выберите быстрый фильтр или воспользуйтесь 🔍 Поиском:',
        'all_cars': '📋 Все'
    },
    'en': {
        'catalog': '🚗 Catalog',
        'search': '🔍 Search',
        'favorites': '❤️ Favorites',
        'saved_searches': '🔖 Saved Searches',
        'ai_recommendations': '🤖 AI Recommendations',
        'price_prediction': '💰 Price Prediction',
        'comparison': '🔄 Compare',
        'main_menu': '🏠 Main Menu',
        'back': '◀️ Back',
        'next': 'Next ▶️',
        'loading': '🔄 Loading...',
        'no_cars': '🔍 No cars found matching your search.',
        'error': '❌ An error occurred',
        'total_found': 'Found {} cars',
        'page': 'Page',
        'price_range': '💰 Price: {} - {} $',
        'brand_filter': '🏷 Brand: {}',
        'cars_found': 'Found {} cars!',
        'catalog_title': 'CAR CATALOG',
        'quick_filters': 'Choose a quick filter or use 🔍 Search:',
        'all_cars': '📋 All'
    }
}

# User language preferences (in production, use database)
user_languages = {}

def get_user_language(user_id: int) -> str:
    """Get user's preferred language"""
    return user_languages.get(user_id, 'uz')

def t(user_id: int, key: str, *args) -> str:
    """Translate text to user's language"""
    lang = get_user_language(user_id)
    text = TRANSLATIONS.get(lang, {}).get(key, key)
    
    if args:
        try:
            return text.format(*args)
        except:
            return text
    return text

def set_user_language(user_id: int, language: str):
    """Set user's preferred language"""
    if language in ['uz', 'ru', 'en']:
        user_languages[user_id] = language

# Simple cache for performance (in production, use Redis)
_cache = {}

def get_cache_key(prefix: str, **kwargs) -> str:
    """Generate cache key"""
    parts = [prefix]
    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}:{v}")
    return ":".join(parts)

def get_from_cache(key: str):
    """Get value from cache"""
    return _cache.get(key)

def set_cache(key: str, value, ttl: int = 300):
    """Set value in cache with TTL"""
    import time
    _cache[key] = {
        'value': value,
        'expires': time.time() + ttl
    }

def is_cache_valid(key: str) -> bool:
    """Check if cache is valid"""
    import time
    if key not in _cache:
        return False
    return _cache[key]['expires'] > time.time()

def clean_expired_cache():
    """Clean expired cache entries"""
    import time
    current_time = time.time()
    expired_keys = [k for k, v in _cache.items() if v['expires'] <= current_time]
    for k in expired_keys:
        del _cache[k]


async def get_ai_recommendations(user_id: int, limit: int = 5):
    """AI-powered car recommendations based on user behavior"""
    try:
        async with async_session_maker() as session:
            # Get user's recent viewed cars
            from database.crud import get_user_views
            recent_views = await get_user_views(session, user_id, limit=10)
            
            # Get user's buy requests
            from database.crud import get_user_buy_requests
            buy_requests = await get_user_buy_requests(session, user_id, limit=5)
            
            # Analyze preferences
            preferred_brands = set()
            preferred_price_range = [0, 100000]
            preferred_years = [2015, 2024]
            
            if recent_views:
                for view in recent_views:
                    preferred_brands.add(view.car.brand)
                    if view.car.price:
                        preferred_price_range[0] = min(preferred_price_range[0], view.car.price * 0.8)
                        preferred_price_range[1] = max(preferred_price_range[1], view.car.price * 1.2)
                    if view.car.year:
                        preferred_years[0] = min(preferred_years[0], view.car.year - 2)
                        preferred_years[1] = max(preferred_years[1], view.car.year + 2)
            
            if buy_requests:
                for req in buy_requests:
                    if req.brand:
                        preferred_brands.add(req.brand)
                    if req.budget_min:
                        preferred_price_range[0] = min(preferred_price_range[0], req.budget_min)
                    if req.budget_max:
                        preferred_price_range[1] = min(preferred_price_range[1], req.budget_max)
            
            # Get recommendations
            recommendations = []
            if preferred_brands:
                for brand in list(preferred_brands)[:3]:  # Top 3 brands
                    cars = await get_cars(
                        session,
                        brand=brand,
                        price_from=preferred_price_range[0],
                        price_to=preferred_price_range[1],
                        limit=2
                    )
                    recommendations.extend(cars)
            
            # If not enough recommendations, get popular cars
            if len(recommendations) < limit:
                popular_cars = await get_cars(
                    session,
                    price_from=preferred_price_range[0],
                    price_to=preferred_price_range[1],
                    limit=limit - len(recommendations)
                )
                recommendations.extend(popular_cars)
            
            return recommendations[:limit]
            
    except Exception as e:
        logger.error(f"Error getting AI recommendations: {e}")
        return []


@router.message(F.text == "🤖 AI Tavsiyalar")
async def ai_recommendations_handler(message: Message):
    """AI-powered car recommendations"""
    try:
        # Show loading
        loading_msg = await message.answer("🤖 AI siz uchun tavsiyalar tayinlayapti...")
        
        recommendations = await get_ai_recommendations(message.from_user.id, limit=5)
        
        await loading_msg.delete()
        
        if not recommendations:
            await message.answer(
                "🤖 <b>AI Tavsiyalari</b>\n\n"
                "Hali sizning afzalliklaringizni aniqlay olmadingiz.\n"
                "Kattaroq moshinalarni ko'ring va qayta urinib ko'ring!",
                parse_mode="HTML"
            )
            return
        
        text = "🤖 <b>AI SIZ UCHUN TAVSIYA QILADI</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "Sizning ko'rishlaringiz asosida:\n\n"
        
        for i, car in enumerate(recommendations, 1):
            text += f"🚗 <b>{i}. {car.brand} {car.model}</b> ({car.year})\n"
            text += f"💰 {car.price:,.0f} $ | 🛣 {car.mileage or 0:,} km\n"
            text += f"⭐ {car.views_count} marta ko'rilgan\n"
            text += "─" * 25 + "\n\n"
        
        # Show recommendations as cars
        await show_car_page(message, recommendations, page=1)
        
        logger.info(f"AI recommendations shown to user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in ai_recommendations_handler: {e}")
        await message.answer(
            "❌ AI tavsiyalarini olishda xatolik yuz berdi.",
            reply_markup=main_menu_keyboard()
        )


async def predict_car_price(brand: str, model: str, year: int, mileage: int = None) -> dict:
    """Predict car price based on market data"""
    try:
        async with async_session_maker() as session:
            # Get similar cars for price analysis
            similar_cars = await get_cars(
                session,
                brand=brand,
                model=model,
                year_from=year - 3,
                year_to=year + 3,
                limit=20
            )
            
            if not similar_cars:
                return {"predicted_price": None, "confidence": 0}
            
            # Calculate price statistics
            prices = [car.price for car in similar_cars if car.price]
            if not prices:
                return {"predicted_price": None, "confidence": 0}
            
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            # Adjust for mileage
            if mileage:
                # Higher mileage reduces price
                avg_mileage = sum([car.mileage or 0 for car in similar_cars]) / len(similar_cars)
                mileage_factor = 1 - ((mileage - avg_mileage) / avg_mileage) * 0.1 if avg_mileage > 0 else 1
                mileage_factor = max(0.7, min(1.3, mileage_factor))  # Limit to ±30%
                avg_price *= mileage_factor
            
            # Adjust for year
            current_year = 2024
            year_factor = 1 - ((current_year - year) * 0.08)  # 8% depreciation per year
            year_factor = max(0.5, year_factor)  # Minimum 50% of original price
            avg_price *= year_factor
            
            # Calculate confidence based on data availability
            confidence = min(0.9, len(similar_cars) / 20)  # More data = higher confidence
            
            return {
                "predicted_price": round(avg_price, 0),
                "price_range": {
                    "min": round(min_price * 0.9, 0),
                    "max": round(max_price * 1.1, 0)
                },
                "confidence": round(confidence, 2),
                "sample_size": len(similar_cars)
            }
            
    except Exception as e:
        logger.error(f"Error predicting car price: {e}")
        return {"predicted_price": None, "confidence": 0}


@router.message(F.text == "💰 Narx Bashorati")
async def price_prediction_handler(message: Message):
    """Car price prediction feature"""
    try:
        await message.answer(
            "💰 <b>NARX BASHORATI</b>\n\n"
            "Mashina ma'lumotlarini kiriting:\n"
            "Format: <b>Brend Model Yil Probeg</b>\n"
            "Masalan: <i>Chevrolet Cobalt 2022 45000</i>\n\n"
            "Probeg ixtiyoriy, km da kiriting.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in price_prediction_handler: {e}")
        await message.answer("❌ Xatolik yuz berdi", reply_markup=main_menu_keyboard())


@router.message(F.text.regexp(r'^[A-Za-z]+\s+[A-Za-z0-9]+\s+\d{4}(\s+\d+)?$'))
async def process_price_prediction(message: Message):
    """Process price prediction request"""
    try:
        parts = message.text.split()
        if len(parts) < 3:
            return
        
        brand = parts[0]
        model = parts[1]
        year = int(parts[2])
        mileage = int(parts[3]) if len(parts) > 3 else None
        
        # Show loading
        loading_msg = await message.answer("🔄 Narx bashorati hisoblanmoqda...")
        
        prediction = await predict_car_price(brand, model, year, mileage)
        
        await loading_msg.delete()
        
        if prediction["predicted_price"]:
            text = f"💰 <b>NARX BASHORATI</b>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            text += f"🚗 <b>{brand} {model}</b> ({year})\n"
            if mileage:
                text += f"🛣 Probeg: {mileage:,} km\n"
            text += f"\n📊 <b>Bashorat qilingan narx:</b>\n"
            text += f"💵 {prediction['predicted_price']:,.0f} $\n\n"
            
            if prediction.get('price_range'):
                text += f"📈 <b>Narx oralig'i:</b>\n"
                text += f"Min: {prediction['price_range']['min']:,.0f} $\n"
                text += f"Max: {prediction['price_range']['max']:,.0f} $\n\n"
            
            text += f"🎯 <b>Ishonch darajasi:</b> {prediction['confidence']*100:.0f}%\n"
            text += f"📊 <b>Analiz qilingan moshinalar:</b> {prediction['sample_size']} ta\n\n"
            
            text += "⚠️ Bu faqat bashorat, haqiqiy narx bozorga qarab farq qilishi mumkin!"
            
        else:
            text = "❌ <b>Narxni bashorat qilib bo'lmadi</b>\n\n"
            text += "Bu model uchun yetarli ma'lumot topilmadi.\n"
            text += "Boshqa mashinalarni sinab ko'ring."
        
        await message.answer(text, parse_mode="HTML")
        logger.info(f"Price prediction for {brand} {model} by user {message.from_user.id}")
        
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "To'g'ri format: <b>Brend Model Yil Probeg</b>\n"
            "Masalan: <i>Chevrolet Cobalt 2022 45000</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error processing price prediction: {e}")
        await message.answer("❌ Bashorat qilishda xatolik yuz berdi")


@router.message(F.text == "🚗 Katalog")
async def catalog_handler(message: Message):
    """Moshinalar katalogi"""
    try:
        # Quick filter keyboard
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💰 5k-10k $", callback_data="quick_filter:price:5000:10000"),
            InlineKeyboardButton(text="💰 10k-15k $", callback_data="quick_filter:price:10000:15000")
        )
        builder.row(
            InlineKeyboardButton(text="💰 15k-20k $", callback_data="quick_filter:price:15000:20000"),
            InlineKeyboardButton(text="💰 20k+ $", callback_data="quick_filter:price:20000:100000")
        )
        builder.row(
            InlineKeyboardButton(text="🏷 Chevrolet", callback_data="quick_filter:brand:Chevrolet"),
            InlineKeyboardButton(text="🏷 Hyundai", callback_data="quick_filter:brand:Hyundai")
        )
        builder.row(
            InlineKeyboardButton(text="🏷 Kia", callback_data="quick_filter:brand:Kia"),
            InlineKeyboardButton(text="🏷 Toyota", callback_data="quick_filter:brand:Toyota")
        )
        builder.row(
            InlineKeyboardButton(text="📋 Barchasi", callback_data="quick_filter:all"),
            InlineKeyboardButton(text="🔄 Solishtirish", callback_data="compare:view")
        )
        builder.row(
            InlineKeyboardButton(text="🔍 Qidiruv", callback_data="go_search")
        )
        
        await message.answer(
            "🚗 <b>MOSHINALAR KATALOGI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Tezkor filtrni tanlang yoki 🔍 Qidiruv orqali toping:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        logger.info(f"User {message.from_user.id} opened catalog")
        
    except Exception as e:
        logger.error(f"Error in catalog_handler: {e}")
        await message.answer(
            "❌ Katalogni ochishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
            reply_markup=main_menu_keyboard()
        )


async def show_car_page(message: Message, cars: list, page: int = 1, edit: bool = False, items_per_page: int = 5):
    """Moshina kartochkasini ko'rsatish (Pagination bilan)"""
    try:
        if not cars:
            await message.answer(
                "🔍 So'rovingiz bo'yicha moshinalar topilmadi.\n"
                "Filtrlarni o'zgartiring yoki kengaytiring.",
                parse_mode="HTML"
            )
            return
        
        total = len(cars)
        total_pages = (total + items_per_page - 1) // items_per_page
        
        if page > total_pages: page = total_pages
        if page < 1: page = 1
        
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_cars = cars[start_idx:end_idx]
        
        # Build compact list view for multiple cars
        text = f"🚗 <b>KATALOG - Sahifa {page}/{total_pages}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"Jami {total} ta moshina topildi\n\n"
        
        for i, car in enumerate(page_cars, 1):
            try:
                color_text = car.color or "ko'rsatilmagan"
                transmission_text = car.transmission or "ko'rsatilmagan"
                fuel_text = car.fuel_type or "ko'rsatilmagan"
                mileage_text = f"{car.mileage:,} km" if car.mileage else "ko'rsatilmagan"
                
                text += (
                    f"<b>{i}. {car.brand} {car.model}</b> ({car.year})\n"
                    f"💰 {car.price:,.0f} $ | 🛣 {mileage_text}\n"
                    f"⚙️ {transmission_text} | ⛽ {fuel_text}\n"
                )
                
                if car.description:
                    desc = car.description[:60]
                    if len(car.description) > 60:
                        desc += "..."
                    text += f"📝 {desc}\n"
                
                text += f"👁 {car.views_count} ko'rish\n"
                text += "─" * 25 + "\n\n"
                
            except Exception as e:
                logger.error(f"Error processing car {i}: {e}")
                text += f"❌ Mashina ma'lumotlarida xatolik\n\n"
        
        # Build keyboard with car selection buttons
        builder = InlineKeyboardBuilder()
        
        # Add buttons for each car on this page
        for i, car in enumerate(page_cars, 1):
            try:
                builder.row(
                    InlineKeyboardButton(
                        text=f"🚗 {i}. {car.brand} {car.model} - {car.price:,.0f} $", 
                        callback_data=f"car:detail:{car.id}"
                    )
                )
            except Exception as e:
                logger.error(f"Error creating button for car {i}: {e}")
        
        # Pagination buttons
        pag_buttons = []
        if page > 1:
            pag_buttons.append(InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"catalog_page:{page-1}"))
        if page < total_pages:
            pag_buttons.append(InlineKeyboardButton(text="Keyingisi ▶️", callback_data=f"catalog_page:{page+1}"))
        
        if pag_buttons:
            builder.row(*pag_buttons)
        
        builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu"))
        
        markup = builder.as_markup()
        
        if edit:
            try:
                await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await message.answer(text, reply_markup=markup, parse_mode="HTML")
            return

        # For new messages, just send text (no photo for list view)
        await message.answer(text, reply_markup=markup, parse_mode="HTML")
        
        logger.info(f"Shown page {page} with {len(page_cars)} cars to user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in show_car_page: {e}")
        await message.answer(
            "❌ Moshinalarni ko'rsatishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text.in_(["🔍 Qidiruv", "🔍 Qidiruv (Filtrlar)"]))
async def search_handler(message: Message, state: FSMContext):
    """Qidiruv — filtrlar bilan"""
    data = await state.get_data()
    
    text = "🔍 <b>MOSHINA QIDIRISH</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    filters_display = ""
    if data.get('filter_brand'):
        filters_display += f"🏷 Brend: <b>{data['filter_brand']}</b>\n"
    if data.get('filter_model'):
        filters_display += f"🚙 Model: <b>{data['filter_model']}</b>\n"
    if data.get('filter_year'):
        filters_display += f"📅 Yil: <b>{data['filter_year']}+</b>\n"
    if data.get('filter_price'):
        filters_display += f"💰 Narx: <b>{data['filter_price']:,.0f} $</b> gacha\n"
    
    if filters_display:
        text += f"📋 <b>Tanlangan filtrlar:</b>\n{filters_display}\n"
        text += "Filtrlarni o'zgartiring yoki qidiruvni boshlang 👇"
    else:
        text += "Qidiruv filtrlarini tanlang.\n"
        text += "Kerakli mezonlarni belgilab, <b>✅ Qidirish</b> tugmasini bosing."
    
    await message.answer(text, reply_markup=car_filters_keyboard(data), parse_mode="HTML")


@router.callback_query(F.data.startswith("filter:"))
async def filter_handler(callback: CallbackQuery, state: FSMContext):
    """Filtr tanlash"""
    filter_type = callback.data.split(":")[1]
    
    async with async_session_maker() as session:
        if filter_type == "brand":
            from database.crud import get_unique_brands
            brands = await get_unique_brands(session)
            if not brands:
                return await callback.answer("📦 Hozircha moshinalar yo'q", show_alert=True)
            
            builder = InlineKeyboardBuilder()
            for b in brands:
                builder.row(InlineKeyboardButton(text=f"🏷 {b}", callback_data=f"select_filter:brand:{b}"))
            builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="filter:back"))
            
            await callback.message.edit_text(
                "🏷 <b>Brendni tanlang:</b>\n\n"
                "Ro'yxatdan birini bosing:",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        
        elif filter_type == "model":
            data = await state.get_data()
            brand = data.get('filter_brand')
            if not brand:
                return await callback.answer("⚠️ Avval brendni tanlang!", show_alert=True)
            
            from database.crud import get_unique_models
            models = await get_unique_models(session, brand)
            if not models:
                return await callback.answer("Bu brendda modellar topilmadi", show_alert=True)
            
            builder = InlineKeyboardBuilder()
            for m in models:
                builder.row(InlineKeyboardButton(text=f"🚙 {m}", callback_data=f"select_filter:model:{m}"))
            builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="filter:back"))
            
            await callback.message.edit_text(
                f"🚙 <b>{brand} modellarini tanlang:</b>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        
        elif filter_type == "year":
            await callback.message.answer(
                "📅 <b>Minimal yilni kiriting:</b>\n"
                "<i>Masalan: 2018 — 2018 yildan keyingi moshinalar ko'rsatiladi</i>",
                parse_mode="HTML"
            )
            await state.set_state(CarSearchStates.waiting_for_year)
            await callback.answer()
        
        elif filter_type == "price":
            await callback.message.answer(
                "💰 <b>Maksimal narxni kiriting (dollarda):</b>\n"
                "<i>Masalan: 15000 — 15 ming dollardan arzon moshinalar</i>",
                parse_mode="HTML"
            )
            await state.set_state(CarSearchStates.waiting_for_price)
            await callback.answer()
        
        elif filter_type == "reset":
            await state.update_data(filter_brand=None, filter_model=None, filter_year=None, filter_price=None)
            await callback.answer("♻️ Barcha filtrlar tozalandi")
            await search_handler(callback.message, state)
        
        elif filter_type == "back":
            await search_handler(callback.message, state)
            await callback.answer()
        
        elif filter_type == "search":
            data = await state.get_data()
            from database.crud import get_cars
            cars = await get_cars(
                session,
                brand=data.get('filter_brand'),
                model=data.get('filter_model'),
                year_from=data.get('filter_year'),
                price_to=data.get('filter_price'),
                limit=50
            )
            
        if cars:
            await callback.message.answer(
                f"✅ <b>{len(cars)} ta moshina topildi!</b>\n"
                "Katalogda ko'rishingiz mumkin:",
                parse_mode="HTML"
            )
            # Store search results in state for pagination if needed
            # For Lite mode, we just show them
            await show_car_page(callback.message, cars, page=1)
        else:
            await callback.answer(
                "❌ Mos moshina topilmadi. Filtrlarni kengaytiring.",
                show_alert=True
            )
        await callback.answer()


@router.callback_query(F.data.startswith("quick_filter:"))
async def quick_filter_handler(callback: CallbackQuery):
    """Tezkor filtrlar"""
    try:
        parts = callback.data.split(":")
        filter_type = parts[1]
        
        # Generate cache key
        cache_key = get_cache_key("quick_filter", type=filter_type, params=":".join(parts[2:]))
        
        # Check cache first
        if is_cache_valid(cache_key):
            cached_data = get_from_cache(cache_key)
            cars = cached_data['value']
            logger.info(f"Cache hit for {cache_key}")
        else:
            # Fetch from database
            async with async_session_maker() as session:
                if filter_type == "price":
                    price_from = float(parts[2])
                    price_to = float(parts[3])
                    cars = await get_cars(session, price_from=price_from, price_to=price_to, limit=50)
                elif filter_type == "brand":
                    brand = parts[2]
                    cars = await get_cars(session, brand=brand, limit=50)
                elif filter_type == "all":
                    cars = await get_cars(session, limit=50)
                else:
                    cars = []
            
            # Cache the results
            set_cache(cache_key, {'value': cars}, ttl=60)  # 1 minute cache
            logger.info(f"Cached {len(cars)} cars for {cache_key}")
        
        if cars:
            filter_text = ""
            if filter_type == "price":
                price_from = float(parts[2])
                price_to = float(parts[3])
                filter_text = f"💰 Narx: {price_from:,.0f} - {price_to:,.0f} $"
            elif filter_type == "brand":
                brand = parts[2]
                filter_text = f"🏷 Brend: {brand}"
            
            await callback.message.answer(
                f"✅ <b>{len(cars)} ta moshina topildi!</b>\n"
                f"{filter_text}\n\n"
                "Katalogda ko'rish:",
                parse_mode="HTML"
            )
            await show_car_page(callback.message, cars, page=1)
        else:
            await callback.answer("❌ Mos moshina topilmadi", show_alert=True)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in quick_filter_handler: {e}")
        await callback.answer("❌ Filtrlashda xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "go_search")
async def go_to_search(callback: CallbackQuery):
    """Qidiruvga o'tish"""
    from handlers.catalog import search_handler
    await search_handler(callback.message, None)
    await callback.answer()


@router.callback_query(F.data.startswith("catalog_page:"))
async def catalog_pagination_handler(callback: CallbackQuery, state: FSMContext):
    """Katalog sahifalari orasida harakatlanish"""
    page = int(callback.data.split(":")[1])
    
    async with async_session_maker() as session:
        # Re-fetch with higher limit for pagination
        cars = await get_cars(session, limit=50)
    
    if cars:
        await show_car_page(callback.message, cars, page=page, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("select_filter:"))
async def select_filter_handler(callback: CallbackQuery, state: FSMContext):
    """Filtr qiymatini tanlash"""
    parts = callback.data.split(":")
    f_type = parts[1]
    f_val = parts[2]
    
    if f_type == "brand":
        await state.update_data(filter_brand=f_val, filter_model=None)
    elif f_type == "model":
        await state.update_data(filter_model=f_val)
    
    await callback.answer(f"✅ Tanlandi: {f_val}")
    await search_handler(callback.message, state)


@router.message(CarSearchStates.waiting_for_year)
async def process_year(message: Message, state: FSMContext):
    """Yil filtrini qabul qilish"""
    if not message.text.isdigit():
        return await message.answer(
            "❌ Iltimos, faqat yilni raqamda kiriting.\n"
            "<i>Masalan: 2020</i>",
            parse_mode="HTML"
        )
    
    year = int(message.text)
    if year < 1990 or year > 2026:
        return await message.answer(
            "❌ 1990 dan 2026 gacha yil kiriting.",
            parse_mode="HTML"
        )
    
    await state.update_data(filter_year=year)
    data = await state.get_data()
    await state.set_state(None)
    await message.answer(
        f"✅ Minimal yil: <b>{year}</b>\n"
        "Boshqa filtrlarni tanlang yoki qidiruvni boshlang:",
        reply_markup=car_filters_keyboard(data),
        parse_mode="HTML"
    )


@router.message(CarSearchStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Narx filtrini qabul qilish"""
    cleaned_price = "".join(filter(str.isdigit, message.text))
    if not cleaned_price:
        return await message.answer(
            "❌ Iltimos, narxni faqat raqamda kiriting.\n"
            "<i>Masalan: 15000</i>",
            parse_mode="HTML"
        )
    
    price = float(cleaned_price)
    await state.update_data(filter_price=price)
    data = await state.get_data()
    await state.set_state(None)
    await message.answer(
        f"✅ Maksimal narx: <b>{price:,.0f} $</b>\n"
        "Boshqa filtrlarni tanlang yoki qidiruvni boshlang:",
        reply_markup=car_filters_keyboard(data),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("car:detail:"))
async def car_detail_handler(callback: CallbackQuery):
    """Show detailed information about a specific car"""
    try:
        # Show loading message
        loading_msg = await callback.message.answer("🔄 Yuklanmoqda...")
        
        car_id = int(callback.data.split(":")[2])
        
        # Check cache first
        cache_key = get_cache_key("car_detail", car_id=car_id)
        
        if is_cache_valid(cache_key):
            cached_data = get_from_cache(cache_key)
            car = cached_data['value']
            logger.info(f"Cache hit for car detail {car_id}")
        else:
            async with async_session_maker() as session:
                car = await get_car_by_id(session, car_id)
                if not car:
                    await loading_msg.delete()
                    await callback.answer("❌ Moshina topilmadi", show_alert=True)
                    return
                
                await increment_car_views(session, car_id)
            
            # Cache car data
            set_cache(cache_key, {'value': car}, ttl=300)  # 5 minutes cache
            logger.info(f"Cached car detail {car_id}")
        
        # Delete loading message
        await loading_msg.delete()
        
        # Build detailed card
        color_text = car.color or "ko'rsatilmagan"
        transmission_text = car.transmission or "ko'rsatilmagan"
        fuel_text = car.fuel_type or "ko'rsatilmagan"
        mileage_text = f"{car.mileage:,} km" if car.mileage else "ko'rsatilmagan"
        
        text = (
            f"🚗 <b>{car.brand} {car.model}</b> ({car.year})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Narxi: <b>{car.price:,.0f} $</b>\n"
            f"📅 Yili: <b>{car.year}</b>\n"
            f"🛣 Probegi: <b>{mileage_text}</b>\n"
            f"⚙️ Uzatma: <b>{transmission_text}</b>\n"
            f"⛽ Yoqilg'i: <b>{fuel_text}</b>\n"
            f"🎨 Rangi: <b>{color_text}</b>\n"
        )
        
        if car.description:
            desc = car.description[:200]
            if len(car.description) > 200:
                desc += "..."
            text += f"\n📝 <b>Tavsif:</b>\n<i>{desc}</i>\n"
        
        if car.expert_notes:
            text += f"\n💎 <b>Ekspert bahosi:</b>\n<i>{car.expert_notes}</i>\n"
        
        text += f"\n👁 Ko'rishlar: {car.views_count}"
        
        # Build action keyboard
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔄 Solishtirish", callback_data=f"compare:add:{car.id}"),
            InlineKeyboardButton(text="❤️", callback_data=f"car:favorite:{car.id}")
        )
        builder.row(
            InlineKeyboardButton(text="📸 Rasmlar", callback_data=f"car:gallery:{car.id}"),
            InlineKeyboardButton(text="⭐ Sharhlar", callback_data=f"car:reviews:{car.id}")
        )
        builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="catalog_page:1"))
        
        await callback.answer()
        
        if car.images and car.images.get('main'):
            try:
                await callback.message.answer_photo(
                    photo=car.images['main'],
                    caption=text,
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
            
        logger.info(f"User {callback.from_user.id} viewed car {car_id}")
        
    except ValueError:
        await callback.answer("❌ Noto'g'ri mashina ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in car_detail_handler: {e}")
        await callback.answer("❌ Ma'lumotlarni yuklashda xatolik", show_alert=True)


# Store comparison cars in state
from aiogram.fsm.context import FSMContext
from states.states import CarSearchStates

# Comparison storage (in production, use Redis or database)
comparison_cars = {}


@router.callback_query(F.data.startswith("compare:add:"))
async def add_to_comparison(callback: CallbackQuery, state: FSMContext):
    """Add car to comparison"""
    car_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    if user_id not in comparison_cars:
        comparison_cars[user_id] = []
    
    if car_id not in comparison_cars[user_id]:
        if len(comparison_cars[user_id]) >= 3:
            await callback.answer("❌ Eng ko'pi bilan 3 ta mashina solishtirish mumkin", show_alert=True)
            return
        
        comparison_cars[user_id].append(car_id)
        await callback.answer(f"✅ Solishtirishga qo'shildi ({len(comparison_cars[user_id])}/3)", show_alert=True)
    else:
        await callback.answer("❌ Bu mashina allaqachon solishtirishda", show_alert=True)


@router.callback_query(F.data == "compare:view")
async def show_comparison(callback: CallbackQuery, state: FSMContext):
    """Show comparison results"""
    user_id = callback.from_user.id
    
    if user_id not in comparison_cars or len(comparison_cars[user_id]) < 2:
        await callback.answer("❌ Kamida 2 ta mashina tanlang", show_alert=True)
        return
    
    async with async_session_maker() as session:
        cars_data = []
        for car_id in comparison_cars[user_id]:
            car = await get_car_by_id(session, car_id)
            if car:
                cars_data.append(car)
    
    if not cars_data:
        await callback.answer("❌ Moshinalar topilmadi", show_alert=True)
        return
    
    # Build comparison table
    text = "🔄 <b>MOSHINALARNI SOLISHTIRISH</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    unknown_text = 'Noma\'lum'
    
    for i, car in enumerate(cars_data, 1):
        text += f"🚗 <b>{i}. {car.brand} {car.model}</b> ({car.year})\n"
        text += f"💰 Narxi: <b>{car.price:,.0f} $</b>\n"
        text += f"🛣 Probeg: <b>{car.mileage or 0:,} km</b>\n"
        text += f"⚙️ Uzatma: <b>{car.transmission or unknown_text}</b>\n"
        text += f"⛽ Yoqilg'i: <b>{car.fuel_type or unknown_text}</b>\n"
        text += "─" * 30 + "\n\n"
    
    # Action buttons
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Tozalash", callback_data="compare:clear"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="catalog_page:1")
    )
    
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "compare:clear")
async def clear_comparison(callback: CallbackQuery):
    """Clear comparison list"""
    user_id = callback.from_user.id
    if user_id in comparison_cars:
        comparison_cars[user_id] = []
    
    await callback.answer("✅ Solishtirish tozalandi", show_alert=True)


async def notify_matching_users(car_id: int):
    """Notify users who have matching buy requests"""
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        if not car:
            return
        
        from database.crud import find_matching_buy_requests
        matching_requests = await find_matching_buy_requests(session, car)
        
        for request in matching_requests:
            try:
                # Send notification to user
                notification_text = (
                    f"🔔 <b>YANGI MOS MASHINA TOPILDI!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🚗 <b>{car.brand} {car.model}</b> ({car.year})\n"
                    f"💰 Narxi: <b>{car.price:,.0f} $</b>\n"
                    f"🛣 Probeg: <b>{car.mileage or 0:,} km</b>\n\n"
                    f"Sizning so'rovingiz #{request.id} ga mos keladi!\n\n"
                    f"📞 Bog'lanish uchun: @Real_Avto_Admin"
                )
                
                # In production, use bot.send_message() with user_id
                # For now, this is a placeholder function
                logger.info(f"Notification sent to user {request.user_id} for car {car_id}")
                
            except Exception as e:
                logger.error(f"Error sending notification to user {request.user_id}: {e}")


@router.callback_query(F.data.startswith("car:favorite:"))
async def toggle_favorite_handler(callback: CallbackQuery):
    """Toggle car favorite status"""
    try:
        car_id = int(callback.data.split(":")[2])
        user_id = callback.from_user.id
        
        if user_id not in user_favorites:
            user_favorites[user_id] = set()
        
        if car_id in user_favorites[user_id]:
            user_favorites[user_id].remove(car_id)
            await callback.answer("❌ Sevimlilardan olib tashlandi", show_alert=True)
        else:
            user_favorites[user_id].add(car_id)
            await callback.answer("❤️ Sevimlilarga qo'shildi", show_alert=True)
        
        logger.info(f"User {user_id} toggled favorite for car {car_id}")
        
    except ValueError:
        await callback.answer("❌ Noto'g'ri mashina ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in toggle_favorite_handler: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.message(F.text == "❤️ Sevimlilar")
async def favorites_handler(message: Message):
    """Show user's favorite cars"""
    try:
        user_id = message.from_user.id
        
        if user_id not in user_favorites or not user_favorites[user_id]:
            await message.answer(
                "❤️ <b>SEVIMLILAR</b>\n\n"
                "Siz hali hech narsani sevimlilarga qo'shmadingiz.\n"
                "Moshinalarni ko'rishda ❤️ tugmasini bosing!",
                parse_mode="HTML"
            )
            return
        
        # Show loading
        loading_msg = await message.answer("🔄 Sevimlilar yuklanmoqda...")
        
        async with async_session_maker() as session:
            favorite_cars = []
            for car_id in user_favorites[user_id]:
                car = await get_car_by_id(session, car_id)
                if car and car.is_available:
                    favorite_cars.append(car)
        
        await loading_msg.delete()
        
        if not favorite_cars:
            await message.answer(
                "❤️ <b>SEVIMLILAR</b>\n\n"
                "Sevimli moshinalaringiz mavjud emas yoki sotuvda yo'q.",
                parse_mode="HTML"
            )
            return
        
        text = f"❤️ <b>SEVIMLILAR ({len(favorite_cars)} ta)</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        await message.answer(text, parse_mode="HTML")
        await show_car_page(message, favorite_cars, page=1)
        
        logger.info(f"User {user_id} viewed {len(favorite_cars)} favorites")
        
    except Exception as e:
        logger.error(f"Error in favorites_handler: {e}")
        await message.answer(
            "❌ Sevimlilarni ko'rsatishda xatolik yuz berdi.",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text == "🔖 Saqlangan Qidiruvlar")
async def saved_searches_handler(message: Message):
    """Show user's saved searches"""
    try:
        user_id = message.from_user.id
        
        if user_id not in user_saved_searches or not user_saved_searches[user_id]:
            await message.answer(
                "🔖 <b>SAQLANGAN QIDIRUVLAR</b>\n\n"
                "Siz hali hech qanday qidiruvni saqlamadingiz.\n"
                "Qidiruv natijalarini saqlash uchun 🔖 tugmasini bosing!",
                parse_mode="HTML"
            )
            return
        
        text = f"🔖 <b>SAQLANGAN QIDIRUVLAR ({len(user_saved_searches[user_id])} ta)</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        builder = InlineKeyboardBuilder()
        
        for i, search in enumerate(user_saved_searches[user_id], 1):
            search_text = f"{search.get('brand', '')} {search.get('model', '')} {search.get('year', '')}"
            search_text = search_text.strip() or "Barcha moshinalar"
            
            text += f"{i}. {search_text}\n"
            text += f"   💰 {search.get('price_min', 0):,.0f}-${search.get('price_max', 999999):,.0f}\n\n"
            
            builder.row(
                InlineKeyboardButton(
                    text=f"🔍 {i}. {search_text[:20]}...",
                    callback_data=f"saved_search:{i-1}"
                )
            )
        
        builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu"))
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in saved_searches_handler: {e}")
        await message.answer(
            "❌ Saqlangan qidiruvlarni ko'rsatishda xatolik yuz berdi.",
            reply_markup=main_menu_keyboard()
        )


@router.callback_query(F.data.startswith("saved_search:"))
async def execute_saved_search(callback: CallbackQuery):
    """Execute a saved search"""
    try:
        search_index = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        
        if user_id not in user_saved_searches or search_index >= len(user_saved_searches[user_id]):
            await callback.answer("❌ Saqlangan qidiruv topilmadi", show_alert=True)
            return
        
        search_params = user_saved_searches[user_id][search_index]
        
        # Show loading
        loading_msg = await callback.message.answer("🔄 Qidiruv bajarilmoqda...")
        
        async with async_session_maker() as session:
            cars = await get_cars(
                session,
                brand=search_params.get('brand'),
                model=search_params.get('model'),
                year_from=search_params.get('year'),
                price_from=search_params.get('price_min'),
                price_to=search_params.get('price_max'),
                limit=50
            )
        
        await loading_msg.delete()
        
        if cars:
            await callback.message.answer(
                f"✅ <b>{len(cars)} ta moshina topildi!</b>\n\n"
                "Saqlangan qidiruv natijalari:",
                parse_mode="HTML"
            )
            await show_car_page(callback.message, cars, page=1)
        else:
            await callback.answer("❌ Mos moshina topilmadi", show_alert=True)
        
        await callback.answer()
        logger.info(f"User {user_id} executed saved search {search_index}")
        
    except Exception as e:
        logger.error(f"Error executing saved search: {e}")
        await callback.answer("❌ Qidiruvni bajarishda xatolik", show_alert=True)


@router.callback_query(F.data.startswith("car:contact:"))
async def car_contact_handler(callback: CallbackQuery):
    """Sotuvchi bilan bog'lanish"""
    car_id = int(callback.data.split(":")[2])
    
    # Increment views
    async with async_session_maker() as session:
        await increment_car_views(session, car_id)
    
    contact_text = (
        "📞 <b>BOG'LANISH MA'LUMOTLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 Telefon: <b>+998 90 123 45 67</b>\n"
        "💬 Telegram: @Real_Avto_Admin\n\n"
        "⏰ Ish vaqti: <b>09:00 — 21:00</b> (har kuni)\n"
        "📍 Manzil: Toshkent shahri\n\n"
        "💡 <i>Moshina ID raqamini aytib, tezroq ma'lumot oling!</i>"
    )
    
    await callback.answer()
    await callback.message.answer(contact_text, parse_mode="HTML")


@router.callback_query(F.data == "need_phone")
async def need_phone_handler(callback: CallbackQuery):
    """Telefon raqam kerak"""
    await callback.answer(
        "📱 Bog'lanish uchun telefon raqamingizni yuboring",
        show_alert=True
    )


@router.callback_query(F.data == "back:catalog")
async def back_to_catalog(callback: CallbackQuery):
    """Katalogga qaytish"""
    await catalog_handler(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("car:share:"))
async def car_share_handler(callback: CallbackQuery):
    """Moshinani ulashish"""
    car_id = int(callback.data.split(":")[2])
    
    bot_username = "avtosavdo_bot"
    share_link = f"https://t.me/{bot_username}?start=car_{car_id}"
    
    await callback.answer()
    await callback.message.answer(
        f"📤 <b>Moshinani ulashish</b>\n\n"
        f"🔗 Havola: {share_link}\n\n"
        f"Do'stlaringiz ham ko'rsin! 😊",
        parse_mode="HTML"
    )


# --- ARZON VARIANTLAR (DEAL FINDER) ---

@router.message(F.text == "📉 Arzon variantlar")
async def cheap_deals_handler(message: Message):
    """Bozordan arzon variantlar"""
    from database.crud import get_good_deals
    
    async with async_session_maker() as session:
        deals = await get_good_deals(session, limit=10)
    
    if not deals:
        await message.answer(
            "📉 <b>Arzon variantlar</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Hozircha bozor narxidan past takliflar topilmadi.\n\n"
            "Har 5 daqiqada bozor tekshiriladi — \n"
            "🔔 Obuna bo'ling, arzon variant chiqqanda xabar keladi!",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        f"📉 <b>Bozordan {len(deals)} ta arzon variant topildi!</b>\n"
        "Eng yaxshisini ko'rsatyapman 👇",
        parse_mode="HTML"
    )
    
    deal = deals[0]
    await show_scraped_deal(message, deal)


async def show_scraped_deal(message: Message, deal):
    """Topilgan arzon e'lonni ko'rsatish"""
    score = getattr(deal, 'deal_score', None)
    if score is None:
        score = 50
        if getattr(deal, 'is_good_deal', False):
            score += 20
        desc = (deal.description or "").lower()
        if 'srochno' in desc or 'tez' in desc:
            score += 10
        if 'naqd' in desc:
            score += 5
        if 'ideal' in desc:
            score += 10
        if 'kraska' in desc or 'dtp' in desc:
            score -= 20
        score = min(100, max(0, score))
    
    if score >= 80:
        score_bar = "🔥🔥🔥🔥🔥"
        score_label = "SUPER DEAL"
    elif score >= 60:
        score_bar = "🔥🔥🔥🔥"
        score_label = "YAXSHI DEAL"
    elif score >= 40:
        score_bar = "⭐⭐⭐"
        score_label = "O'RTACHA"
    else:
        score_bar = "⭐⭐"
        score_label = "ODDIY"
    
    desc_short = (deal.description or "")[:200].replace('\n', ' ')
    if len(deal.description or "") > 200:
        desc_short += "..."
    
    text = (
        f"📉 <b>ARZON VARIANT — {score_label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{score_bar} Deal balli: <b>{score}/100</b>\n\n"
        f"🚗 <b>{deal.brand} {deal.model}</b> ({deal.year})\n"
        f"💰 Narxi: <b>{deal.price:,.0f} $</b>\n\n"
        f"🛣 Probegi: <b>{deal.mileage or 0:,} km</b>\n"
        f"⚙️ Uzatma: <b>{deal.transmission or 'Aniqlanmadi'}</b>\n"
        f"⛽ Yoqilg'i: <b>{deal.fuel_type or 'Aniqlanmadi'}</b>\n"
    )
    
    if desc_short:
        text += f"\n📝 <i>{desc_short}</i>\n"
    
    text += (
        f"\n📍 Joylashuv: <b>{deal.location or 'Toshkent'}</b>\n"
        f"🌐 Manba: <b>{deal.source.upper()}</b>"
    )
    
    markup = scraped_listing_keyboard(deal.url, deal.source)
    
    if deal.images and deal.images.get('main'):
        try:
            await message.answer_photo(
                photo=deal.images['main'],
                caption=text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        except Exception:
            await message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        # No main image
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.message(F.text & ~F.text.startswith('/'))
async def smart_search(message: Message, state: FSMContext):
    """
    Aqlli qidiruv (Smart Search)
    Foydalanuvchi "Gentra 2020" yoki "Cobalt oq" deb yozganda ishlaydi.
    """
    # Ignore commands or specific menu items handled elsewhere
    if message.text.startswith("/") or message.text in ["🚗 Katalog", "🔍 Qidiruv", "📉 Arzon variantlar", "🏠 Bosh menyu"]:
        return

    text = message.text.lower()
    
    # Simple extraction logic
    brand = None
    model = None
    year = None
    price = None
    
    # Brands & Models
    keywords = {
        'cobalt': ('Chevrolet', 'Cobalt'),
        'gentra': ('Chevrolet', 'Gentra'),
        'lacetti': ('Chevrolet', 'Lacetti'),
        'malibu': ('Chevrolet', 'Malibu'),
        'tracker': ('Chevrolet', 'Tracker'),
        'spark': ('Chevrolet', 'Spark'),
        'nexia': ('Chevrolet', 'Nexia'),
        'damas': ('Chevrolet', 'Damas'),
        'kia': ('Kia', None),
        'k5': ('Kia', 'K5'),
        'hyundai': ('Hyundai', None),
        'santa fe': ('Hyundai', 'Santa Fe'),
        'sonata': ('Hyundai', 'Sonata'),
        'toyota': ('Toyota', None),
        'camry': ('Toyota', 'Camry'),
        'prado': ('Toyota', 'Prado'),
        'byd': ('BYD', None),
        'song': ('BYD', 'Song'),
        'han': ('BYD', 'Han'),
    }
    
    for key, (b, m) in keywords.items():
        if key in text:
            brand = b
            if m: model = m
            break
            
    # Year (e.g. 2020)
    import re
    year_match = re.search(r'\b(20\d{2})\b', text)
    if year_match:
        year = int(year_match.group(1))
        
    # Price (e.g. 15000, 15k, 15 ming)
    # This acts as max price
    price_match = re.search(r'\b(\d{2,5})\b', text)
    if price_match:
        val = int(price_match.group(1))
        # Logic: if < 100 assume it's thousands (e.g. 15 = 15000)
        # if > 1000 assume exact
        if val < 100: 
            price = val * 1000
        elif val > 1000:
            price = val

    # Perform search if at least Brand is found
    if brand or model or year or price:
        async with async_session_maker() as session:
            cars = await get_cars(
                session,
                brand=brand,
                model=model,
                year_from=year,
                price_to=price,
                limit=50
            )
            
        if cars:
            await message.answer(
                f"🔍 <b>Qidiruv natijalari:</b>\n"
                f"{brand or ''} {model or ''} {year or ''} {price or ''}\n\n"
                f"✅ {len(cars)} ta moshina topildi!",
                parse_mode="HTML"
            )
            await show_car_page(message, cars, page=1)
        else:
            await message.answer(
                "😔 So'rovingiz bo'yicha hech narsa topilmadi.\n"
                "Boshqa parametrlarni sinab ko'ring.",
                parse_mode="HTML"
            )
    else:
        # If no keywords found, maybe it's just chatter. 
        # But we can respond nicely as a help tip.
        await message.answer(
            "🤖 <b>Men moshina qidirish yordamchisiman!</b>\n\n"
            "Menga shunday yozishingiz mumkin:\n"
            "🔹 <i>Gentra 2022</i>\n"
            "🔹 <i>Cobalt oq</i>\n"
            "🔹 <i>15000 gacha Malibu</i>",
            parse_mode="HTML"
        )
