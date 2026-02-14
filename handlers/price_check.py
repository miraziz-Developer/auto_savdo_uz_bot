"""
Price Check Handler — Narxni Baholash
Klient moshina brendini va modelini kiritadi, 
tizim bozor narxini, min/max va likvidlikni ko'rsatadi.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from states.states import PriceCheckStates
from database.database import async_session_maker
from database.crud import get_average_market_price, get_price_range, get_active_competitors_count
from keyboards.user_keyboards import main_menu_keyboard, cancel_keyboard

router = Router()

LIQUIDITY_MAP = {
    'gentra': {'time': '1-3 kun', 'emoji': '🔥🔥🔥', 'level': 'Juda tez'},
    'cobalt': {'time': '1-3 kun', 'emoji': '🔥🔥🔥', 'level': 'Juda tez'},
    'spark': {'time': '2-5 kun', 'emoji': '🔥🔥', 'level': 'Tez'},
    'nexia': {'time': '3-5 kun', 'emoji': '🔥🔥', 'level': 'Tez'},
    'nexia 3': {'time': '2-4 kun', 'emoji': '🔥🔥', 'level': 'Tez'},
    'damas': {'time': '1-2 kun', 'emoji': '🔥🔥🔥', 'level': 'Juda tez'},
    'malibu': {'time': '5-10 kun', 'emoji': '🔥', 'level': 'O\'rtacha'},
    'tracker': {'time': '7-14 kun', 'emoji': '🔥', 'level': 'O\'rtacha'},
    'lacetti': {'time': '3-7 kun', 'emoji': '🔥🔥', 'level': 'Tez'},
    'matiz': {'time': '3-7 kun', 'emoji': '🔥🔥', 'level': 'Tez'},
    'camry': {'time': '7-15 kun', 'emoji': '🔥', 'level': 'O\'rtacha'},
    'accent': {'time': '5-10 kun', 'emoji': '🔥', 'level': 'O\'rtacha'},
    'sonata': {'time': '7-14 kun', 'emoji': '🔥', 'level': 'O\'rtacha'},
    'k5': {'time': '10-20 kun', 'emoji': '⭐', 'level': 'Sekin'},
    'captiva': {'time': '10-20 kun', 'emoji': '⭐', 'level': 'Sekin'},
    'equinox': {'time': '10-20 kun', 'emoji': '⭐', 'level': 'Sekin'},
}


from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

POPULAR_BRANDS_MAP = {
    "Chevrolet": ["Gentra", "Cobalt", "Nexia 3", "Spark", "Malibu", "Tracker", "Lacetti", "Damas", "Captiva", "Equinox"],
    "Hyundai": ["Accent", "Sonata", "Tucson", "Elantra", "Santa Fe"],
    "Kia": ["K5", "Sportage", "Seltos", "Rio", "Cerato"],
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser"],
    "Daewoo": ["Nexia", "Matiz", "Tico"],
}


@router.message(F.text.in_(["📊 Narxni baholash", "💲 Narx tekshirish"]))
async def start_price_check(message: Message, state: FSMContext):
    """Start price check flow"""
    await state.clear()
    
    brands = list(POPULAR_BRANDS_MAP.keys())
    builder = []
    for i in range(0, len(brands), 2):
        row = [KeyboardButton(text=brands[i])]
        if i + 1 < len(brands):
            row.append(KeyboardButton(text=brands[i+1]))
        builder.append(row)
    builder.append([KeyboardButton(text="❌ Bekor qilish")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    
    await message.answer(
        "📊 <b>NARXNI BAHOLASH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Real bozor narxlarini bilib oling!\n"
        "Moshina brendi, modeli va yilini kiriting —\n"
        "bozor tahlilini ko'rsatamiz.\n\n"
        "🏷 <b>Brendni tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(PriceCheckStates.waiting_for_brand)


@router.message(PriceCheckStates.waiting_for_brand)
async def process_brand(message: Message, state: FSMContext):
    """Process brand for price check"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ <b>Bekor qilindi</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return
    
    brand = message.text.strip()
    await state.update_data(brand=brand)
    
    # Show models
    models = POPULAR_BRANDS_MAP.get(brand, [])
    if models:
        builder = [[KeyboardButton(text=m)] for m in models]
    else:
        builder = []
    builder.append([KeyboardButton(text="❌ Bekor qilish")])
    keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    
    await message.answer(
        f"✅ Brend: <b>{brand}</b>\n\n"
        "🚙 <b>Model nomini tanlang yoki yozing:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(PriceCheckStates.waiting_for_model)


@router.message(PriceCheckStates.waiting_for_model)
async def process_model(message: Message, state: FSMContext):
    """Process model"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ <b>Bekor qilindi</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return
    
    model = message.text.strip()
    await state.update_data(model=model)
    
    # Year
    current_year = 2026
    years = [str(y) for y in range(current_year, current_year - 12, -1)]
    builder = []
    for i in range(0, len(years), 4):
        row = [KeyboardButton(text=y) for y in years[i:i+4]]
        builder.append(row)
    builder.append([KeyboardButton(text="❌ Bekor qilish")])
    keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    
    await message.answer(
        f"✅ Model: <b>{model}</b>\n\n"
        "📅 <b>Yilni tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(PriceCheckStates.waiting_for_year)


@router.message(PriceCheckStates.waiting_for_year)
async def process_year(message: Message, state: FSMContext):
    """Process year and show price analysis"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ <b>Bekor qilindi</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return
    
    try:
        year = int(message.text.strip())
    except ValueError:
        await message.answer("❌ To'g'ri yil kiriting")
        return
    
    data = await state.get_data()
    brand = data['brand']
    model = data['model']
    
    await state.clear()
    await message.answer(
        "⏳ <b>Bozor ma'lumotlari tahlil qilinmoqda...</b>\n"
        "<i>Bir soniya kuting</i>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    
    async with async_session_maker() as session:
        # Get market data
        avg_price = await get_average_market_price(session, brand, model, year)
        price_range = await get_price_range(session, brand, model, year)
        competitors = await get_active_competitors_count(session, brand, model, year, avg_price if avg_price else 0)
    
    # Liquidity
    model_lower = model.lower()
    liq = LIQUIDITY_MAP.get(model_lower, {'time': '7-14 kun', 'emoji': '⭐', 'level': 'O\'rtacha'})
    
    if price_range['count'] == 0 and avg_price == 0:
        await message.answer(
            f"📊 <b>{brand} {model} ({year})</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ Bu moshina bo'yicha yetarli ma'lumot topilmadi.\n\n"
            "Bozorda kam uchraydi yoki boshqa nom\n"
            "bilan joylashtirilgan bo'lishi mumkin.\n\n"
            "📞 Savdogarimiz bilan bog'laning:\n"
            "@avtosavdo_admin",
            parse_mode="HTML"
        )
        return
    
    # Build beautiful report
    text = f"📊 <b>BOZOR NARX TAHLILI</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🚗 <b>{brand} {model} ({year})</b>\n\n"
    
    if avg_price:
        text += f"💰 <b>O'rtacha narx: {avg_price:,.0f} $</b>\n"
    
    if price_range['count'] > 0:
        text += f"📉 Eng arzon: <b>{price_range['min_price']:,.0f} $</b>\n"
        text += f"📈 Eng qimmat: <b>{price_range['max_price']:,.0f} $</b>\n"
        text += f"📊 E'lonlar soni: <b>{price_range['count']} ta</b>\n"
    
    text += f"\n{liq['emoji']} Likvidlik: <b>{liq['level']} ({liq['time']})</b>\n"
    
    if competitors:
        text += f"🏪 Raqobatchilar: <b>{competitors} ta</b>\n"
    
    # Price recommendations
    if avg_price:
        text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💡 <b>TAVSIYALAR:</b>\n\n"
        
        buy_price = avg_price * 0.92  # 8% past
        sell_price = avg_price * 1.03  # 3% yuqori
        flip_profit = sell_price - buy_price
        
        text += f"🟢 Yaxshi olish narxi: <b>{buy_price:,.0f} $</b>\n"
        text += f"🔵 Yaxshi sotish narxi: <b>{sell_price:,.0f} $</b>\n"
        text += f"💵 Taxminiy foyda: <b>{flip_profit:,.0f} $</b>\n\n"
        
        if avg_price < 10000:
            text += "📈 <i>Arzon segment — tez sotiladi, lekin foyda kam</i>\n"
        elif avg_price < 20000:
            text += "📈 <i>O'rta segment — eng ko'p talab, yaxshi foyda</i>\n"
        else:
            text += "📈 <i>Yuqori segment — uzoqroq sotiladi, lekin foyda yuqori</i>\n"
    
    text += f"\n⏰ <i>Ma'lumot: so'nggi 14 kun ichidagi e'lonlardan</i>"
    
    await message.answer(text, parse_mode="HTML")
