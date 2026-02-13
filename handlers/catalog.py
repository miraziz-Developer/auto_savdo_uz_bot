"""
User handlers for catalog and car browsing
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from loguru import logger

from database.database import async_session_maker
from database.crud import get_cars, get_car_by_id, increment_car_views, update_user_phone
from keyboards.user_keyboards import (
    car_filters_keyboard, car_detail_keyboard, 
    pagination_keyboard, request_phone_keyboard, main_menu_keyboard,
    scraped_listing_keyboard
)
from states.states import CarSearchStates

router = Router()

# Temporary storage for search filters (in production, use Redis)
user_filters = {}


@router.message(F.text == "🚗 Katalog")
async def catalog_handler(message: Message):
    """Show car catalog"""
    async with async_session_maker() as session:
        cars = await get_cars(session, limit=10)
    
    if not cars:
        await message.answer(
            "❌ Hozirda moshinalar mavjud emas.\n\n"
            "Tez orada yangi moshinalar qo'shiladi!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Show first page
    await show_car_page(message, cars, page=1)


async def show_car_page(message: Message, cars: list, page: int = 1):
    """Display a page of cars"""
    if not cars:
        await message.answer("Moshinalar topilmadi ❌")
        return
    
    # Show one car per page for better UX
    car = cars[0] if cars else None
    
    if not car:
        return
    
    # Build car description
    color_text = car.color or "Ko'rsatilmagan"
    transmission_text = car.transmission or "Ko'rsatilmagan"
    fuel_text = car.fuel_type or "Ko'rsatilmagan"
    
    text = f"""
⭐ <b>{car.brand} {car.model}</b>

📅 Yili: <b>{car.year}</b>
💰 Narxi: <b>{car.price:,.0f} $</b>
🎨 Rangi: <b>{color_text}</b>
⚙️ Karobkasi: <b>{transmission_text}</b>
⛽ Yoqilg'i: <b>{fuel_text}</b>
🛣 Probegi: <b>{car.mileage:,} km</b>

📝 <b>Ma'lumot:</b>
{car.description or "Ma'lumot berilmagan"}

👁 Ko'rishlar: <b>{car.views_count}</b>
"""
    
    if car.expert_notes:
        text += f"\n\n💎 <b>Ekspert xulosasi:</b>\n<i>{car.expert_notes}</i>"
    
    # Send car image if available
    if car.images and car.images.get('main'):
        try:
            await message.answer_photo(
                photo=car.images['main'],
                caption=text,
                reply_markup=car_detail_keyboard(car.id, has_phone=True)
            )
        except:
            await message.answer(
                text,
                reply_markup=car_detail_keyboard(car.id, has_phone=True)
            )
    else:
        await message.answer(
            text,
            reply_markup=car_detail_keyboard(car.id, has_phone=True)
        )


@router.message(F.text == "🔍 Qidiruv")
async def search_handler(message: Message, state: FSMContext):
    """Start car search"""
    data = await state.get_data()
    
    text = "🔍 **Moshina qidirish**\n\n"
    filters_display = ""
    if data.get('filter_brand'): filters_display += f"🏷 Brend: {data['filter_brand']}\n"
    if data.get('filter_model'): filters_display += f"🚙 Model: {data['filter_model']}\n"
    if data.get('filter_year'): filters_display += f"📅 Yil: {data['filter_year']}+\n"
    if data.get('filter_price'): filters_display += f"💰 Narx: {data['filter_price']:,.0f} $ gacha\n"
    
    if filters_display:
        text += f"**Hozirgi filtrlar:**\n{filters_display}\n"
    else:
        text += "Hozircha hech qanday filtr tanlanmagan."
        
    await message.answer(text, reply_markup=car_filters_keyboard(data))


@router.callback_query(F.data.startswith("filter:"))
async def filter_handler(callback: CallbackQuery, state: FSMContext):
    """Handle filter selections"""
    filter_type = callback.data.split(":")[1]
    
    async with async_session_maker() as session:
        if filter_type == "brand":
            from database.crud import get_unique_brands
            brands = await get_unique_brands(session)
            if not brands:
                return await callback.answer("Hozircha moshinalar yo'q", show_alert=True)
            
            builder = InlineKeyboardBuilder()
            for b in brands:
                builder.row(InlineKeyboardButton(text=b, callback_data=f"select_filter:brand:{b}"))
            builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="filter:back"))
            
            await callback.message.edit_text("🔍 **Brendni tanlang:**", reply_markup=builder.as_markup())
        
        elif filter_type == "model":
            data = await state.get_data()
            brand = data.get('filter_brand')
            if not brand:
                return await callback.answer("Avval brendni tanlang!", show_alert=True)
            
            from database.crud import get_unique_models
            models = await get_unique_models(session, brand)
            builder = InlineKeyboardBuilder()
            for m in models:
                builder.row(InlineKeyboardButton(text=m, callback_data=f"select_filter:model:{m}"))
            builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="filter:back"))
            
            await callback.message.edit_text(f"🔍 **{brand} modellarini tanlang:**", reply_markup=builder.as_markup())
        
        elif filter_type == "year":
            await callback.message.answer("📅 **Minimal yilni kiriting:**\n<i>(Masalan: 2018)</i>", parse_mode="HTML")
            await state.set_state(CarSearchStates.waiting_for_year)
            await callback.answer()
        
        elif filter_type == "price":
            await callback.message.answer("💰 **Maksimal narxni kiriting (USD):**\n<i>(Masalan: 12000)</i>", parse_mode="HTML")
            await state.set_state(CarSearchStates.waiting_for_price)
            await callback.answer()
        
        elif filter_type == "reset":
            await state.update_data(filter_brand=None, filter_model=None, filter_year=None, filter_price=None)
            await callback.answer("Filtrlar tozalandi ♻️")
            await search_handler(callback.message, state) # Refresh menu
        
        elif filter_type == "back":
            await search_handler(callback.message, state)
        
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
                await callback.message.answer(f"✅ {len(cars)} ta moshina topildi!")
                await show_car_page(callback.message, cars, page=1)
            else:
                await callback.answer("❌ Mos moshina topilmadi", show_alert=True)


@router.callback_query(F.data.startswith("select_filter:"))
async def select_filter_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    f_type = parts[1]
    f_val = parts[2]
    
    if f_type == "brand":
        await state.update_data(filter_brand=f_val, filter_model=None) # Reset model if brand changes
    elif f_type == "model":
        await state.update_data(filter_model=f_val)
        
    await callback.answer(f"Tanlandi: {f_val}")
    await search_handler(callback.message, state)


@router.message(CarSearchStates.waiting_for_year)
async def process_year(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("🔢 Faqat son kiriting (yil):")
    
    year = int(message.text)
    await state.update_data(filter_year=year)
    await message.answer(f"✅ Minimal yil: {year}\nBoshqa filtrlarni tanlang:", reply_markup=car_filters_keyboard())
    await state.set_state(None)


@router.message(CarSearchStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    cleaned_price = "".join(filter(str.isdigit, message.text))
    if not cleaned_price:
        return await message.answer("🔢 Narxni sonda kiriting ($):")
    
    price = float(cleaned_price)
    await state.update_data(filter_price=price)
    await message.answer(f"✅ Maksimal narx: {price:,.0f} $\nBoshqa filtrlarni tanlang:", reply_markup=car_filters_keyboard())
    await state.set_state(None)


@router.callback_query(F.data.startswith("car:contact:"))
async def car_contact_handler(callback: CallbackQuery):
    """Handle contact request for a car"""
    car_id = int(callback.data.split(":")[2])
    
    contact_text = """
📞 **Bog'lanish**

Telefon: +998 90 123 45 67
Telegram: @avtosavdo_admin

⏰ Ish vaqti: 9:00 - 20:00 (har kuni)
    """
    
    await callback.answer()
    await callback.message.answer(contact_text)


@router.callback_query(F.data == "back:catalog")
async def back_to_catalog(callback: CallbackQuery):
    """Go back to catalog view"""
    await catalog_handler(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("car:share:"))
async def car_share_handler(callback: CallbackQuery):
    """Share car"""
    car_id = int(callback.data.split(":")[2])
    
    # Create share link
    bot_username = "avtosavdo_bot"  # Replace with actual bot username
    share_link = f"https://t.me/{bot_username}?start=car_{car_id}"
    
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 Bu moshinani ulashish uchun link:\n\n{share_link}"
    )


# --- CHEAP DEALS (FLIPPER MODE) ---
@router.message(F.text == "📉 Arzon variantlar")
async def cheap_deals_handler(message: Message):
    """Show cheap/good deals from market"""
    from database.crud import get_good_deals
    
    async with async_session_maker() as session:
        deals = await get_good_deals(session, limit=10)
    
    if not deals:
        await message.answer(
            "😢 Hozircha super chegirmalar topilmadi.\n"
            "Bozorni kuzatib boryapmiz, keyinroq qaytib ko'ring!"
        )
        return

    # Show first deal as a "Feed" style
    # Or show gallery? For now, show the best one first.
    deal = deals[0]
    await show_scraped_deal(message, deal)


async def show_scraped_deal(message: Message, deal):
    """Display a scraped listing"""
    score = getattr(deal, 'deal_score', None)
    if score is None:
        # Calculate on the fly if not present
        score = 50
        if getattr(deal, 'is_good_deal', False): score += 20
        desc = (deal.description or "").lower()
        if 'srochno' in desc or 'tez' in desc: score += 10
        if 'naqd' in desc: score += 5
        if 'ideal' in desc: score += 10
        if 'kraska' in desc or 'dtp' in desc: score -= 20
        score = min(100, max(0, score))
    emoji = "🔥" if score > 80 else "⭐"
    
    desc_short = (deal.description or "")[:150].replace('\n', ' ')
    
    text = f"""
{emoji} <b>DEAL BALLI: {score}/100</b>
📉 <b>ARZON VARIANT!</b>

🚘 <b>{deal.brand} {deal.model}</b> ({deal.year})
💰 Narxi: <b>{deal.price:,.0f} $</b>

🛣 Probeg: <b>{deal.mileage} km</b>
⚙️ Karobka: <b>{deal.transmission or "?"}</b>
⛽ Yoqilg'i: <b>{deal.fuel_type or "?"}</b>

📝 <i>{desc_short}...</i>

📍 Manzil: <b>{deal.location or "Toshkent"}</b>
🌐 Manba: {deal.source.upper()}
"""
    
    markup = scraped_listing_keyboard(deal.url, deal.source)
    
    if deal.images and deal.images.get('main'):
        try:
            await message.answer_photo(
                photo=deal.images['main'],
                caption=text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        except:
             await message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")
