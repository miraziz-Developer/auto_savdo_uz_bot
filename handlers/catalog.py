"""
Catalog — Moshinalar katalogi, qidiruv, filtrlar
Foydalanuvchi moshinalarni ko'radi, filtrlaydi, bog'lanadi
"""
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
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


@router.message(F.text == "🚗 Katalog")
async def catalog_handler(message: Message):
    """Moshinalar katalogi"""
    async with async_session_maker() as session:
        cars = await get_cars(session, limit=10)
    
    if not cars:
        await message.answer(
            "📦 <b>Hozirda katalogda moshinalar yo'q</b>\n\n"
            "Tez orada yangi moshinalar qo'shiladi!\n"
            "🔔 Obuna bo'lib turing — yangi e'lon chiqqanda xabar beramiz.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await show_car_page(message, cars, page=1)


async def show_car_page(message: Message, cars: list, page: int = 1):
    """Moshina kartochkasini ko'rsatish"""
    if not cars:
        await message.answer(
            "🔍 So'rovingiz bo'yicha moshinalar topilmadi.\n"
            "Filtrlarni o'zgartiring yoki kengaytiring.",
            parse_mode="HTML"
        )
        return
    
    car = cars[0] if cars else None
    if not car:
        return
    
    # Build card
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
    
    if car.images and car.images.get('main'):
        try:
            await message.answer_photo(
                photo=car.images['main'],
                caption=text,
                reply_markup=car_detail_keyboard(car.id, has_phone=True),
                parse_mode="HTML"
            )
        except Exception:
            await message.answer(
                text,
                reply_markup=car_detail_keyboard(car.id, has_phone=True),
                parse_mode="HTML"
            )
    else:
        await message.answer(
            text,
            reply_markup=car_detail_keyboard(car.id, has_phone=True),
            parse_mode="HTML"
        )


@router.message(F.text == "🔍 Qidiruv")
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
                    "Birinchisini ko'rsatyapman:",
                    parse_mode="HTML"
                )
                await show_car_page(callback.message, cars, page=1)
            else:
                await callback.answer(
                    "❌ Mos moshina topilmadi. Filtrlarni kengaytiring.",
                    show_alert=True
                )
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
    await state.set_state(None)
    await message.answer(
        f"✅ Minimal yil: <b>{year}</b>\n"
        "Boshqa filtrlarni tanlang yoki qidiruvni boshlang:",
        reply_markup=car_filters_keyboard({'filter_year': year}),
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
    await state.set_state(None)
    await message.answer(
        f"✅ Maksimal narx: <b>{price:,.0f} $</b>\n"
        "Boshqa filtrlarni tanlang yoki qidiruvni boshlang:",
        reply_markup=car_filters_keyboard({'filter_price': price}),
        parse_mode="HTML"
    )


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
        "💬 Telegram: @avtosavdo_admin\n\n"
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
        f"⚙️ Uzatma: <b>{deal.transmission or 'noma\'lum'}</b>\n"
        f"⛽ Yoqilg'i: <b>{deal.fuel_type or 'noma\'lum'}</b>\n"
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
        await message.answer(text, reply_markup=markup, parse_mode="HTML")
