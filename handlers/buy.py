"""
Buy Request Handler — Moshina olmoqchiman
Klient nima moshinani xohlashini to'liq oladi va admin'ga yuboradi.
Avtomatik mos variantlarni topadi va taklif qiladi.
"""
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from loguru import logger

from states.states import BuyRequestStates
from config import settings
from database.database import async_session_maker
from database.crud import (
    create_buy_request, get_user_by_id, update_user_lead_data,
    find_matching_cars_for_request, schedule_followups_for_buy_request,
    get_buy_request_by_id, get_user_buy_requests
)
from utils.lead_scoring import (
    calculate_inquiry_lead_score, calculate_user_lead_score,
    detect_urgency_keywords, get_urgency_emoji, get_urgency_text,
    get_lead_score_emoji
)
from keyboards.user_keyboards import main_menu_keyboard, cancel_keyboard

router = Router()

# Popular brands
POPULAR_BRANDS = [
    "Chevrolet", "Hyundai", "Kia", "Toyota", "Daewoo",
    "Nissan", "BMW", "Mercedes", "Volkswagen", "Lada"
]

POPULAR_MODELS = {
    "chevrolet": ["Gentra", "Cobalt", "Nexia 3", "Spark", "Malibu", "Tracker", "Equinox", "Lacetti", "Captiva", "Damas"],
    "hyundai": ["Accent", "Sonata", "Tucson", "Elantra", "Santa Fe", "Creta", "Kona"],
    "kia": ["K5", "Sportage", "Seltos", "Rio", "Cerato", "Sorento"],
    "toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Prado", "Hilux"],
    "daewoo": ["Gentra", "Cobalt", "Nexia", "Matiz", "Damas", "Tico"],
    "nissan": ["Almera", "Qashqai", "X-Trail", "Pathfinder"],
    "lada": ["Vesta", "Granta", "Niva"],
}

TRANSMISSIONS = ["Avtomat", "Mexanika", "Hammasi bo'ladi"]
FUEL_TYPES = ["Benzin", "Gas (Metan)", "Gas (Propan)", "Dizel", "Gibrid", "Hammasi"]
COLORS = ["Oq", "Qora", "Kumush/Kulrang", "Ko'k", "Qizil", "Boshqa", "Farqi yo'q"]


@router.message(F.text.in_(["🛒 Moshina olish", "🛒 Sotib olish"]))
async def start_buy_request(message: Message, state: FSMContext):
    """Start buy request flow"""
    await state.clear()
    
    builder = []
    for i in range(0, len(POPULAR_BRANDS), 2):
        row = [KeyboardButton(text=POPULAR_BRANDS[i])]
        if i + 1 < len(POPULAR_BRANDS):
            row.append(KeyboardButton(text=POPULAR_BRANDS[i + 1]))
        builder.append(row)
    builder.append([KeyboardButton(text="❌ Bekor qilish")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    
    await message.answer(
        "🛒 <b>MOSHINA SOTIB OLISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Nimani xohlaysiz — biz topamiz!\n"
        "Ariza to'ldiring — mutaxassislarimiz sizga\n"
        "eng yaxshi variantlarni taklif qiladi.\n\n"
        "📌 <b>1-qadam:</b> Brendni tanlang yoki yozing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_brand)


@router.message(BuyRequestStates.waiting_for_brand)
async def process_brand(message: Message, state: FSMContext):
    """Process brand selection"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ <b>Ariza bekor qilindi</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return
    
    brand = message.text.strip()
    await state.update_data(brand=brand)
    
    # Show models
    brand_lower = brand.lower()
    models = POPULAR_MODELS.get(brand_lower, [])
    
    if models:
        builder = []
        for i in range(0, len(models), 2):
            row = [KeyboardButton(text=models[i])]
            if i + 1 < len(models):
                row.append(KeyboardButton(text=models[i + 1]))
            builder.append(row)
        builder.append([KeyboardButton(text="Barcha modellar")])
        builder.append([KeyboardButton(text="❌ Bekor qilish")])
        keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Barcha modellar")],
                [KeyboardButton(text="❌ Bekor qilish")]
            ],
            resize_keyboard=True
        )
    
    await message.answer(
        f"✅ Brend: <b>{brand}</b>\n\n"
        "📌 <b>2-qadam:</b> Modelni tanlang yoki yozing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_model)


@router.message(BuyRequestStates.waiting_for_model)
async def process_model(message: Message, state: FSMContext):
    """Process model selection"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    model = message.text.strip() if message.text != "Barcha modellar" else None
    await state.update_data(model=model)
    
    # Years keyboard (Range buttons)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="2024 - 2026"), KeyboardButton(text="2020 - 2023")],
            [KeyboardButton(text="2016 - 2019"), KeyboardButton(text="2010 - 2015")],
            [KeyboardButton(text="2000 - 2009"), KeyboardButton(text="Farqi yo'q")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    data = await state.get_data()
    await message.answer(
        f"✅ Brend: <b>{data['brand']}</b>\n"
        f"✅ Model: <b>{model or 'Barcha'}</b>\n\n"
        "📌 <b>3-qadam:</b> Yilni tanlang yoki yozing:\n"
        "<i>Diapazon ham mumkin, masalan: 2018-2022</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_year)


@router.message(BuyRequestStates.waiting_for_year)
async def process_year(message: Message, state: FSMContext):
    """Process year selection"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    if message.text == "Farqi yo'q":
        await state.update_data(year_from=None, year_to=None)
    elif "-" in message.text:
        parts = message.text.split("-")
        try:
            year_from = int(parts[0].strip())
            year_to = int(parts[1].strip())
            await state.update_data(year_from=year_from, year_to=year_to)
        except ValueError:
            await message.answer("❌ Noto'g'ri format. Masalan: 2018-2022")
            return
    else:
        try:
            year = int(message.text.strip())
            await state.update_data(year_from=year, year_to=2026)
        except ValueError:
            await message.answer("❌ To'g'ri yil kiriting (masalan: 2020)")
            return
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="5k - 8k $"), KeyboardButton(text="8k - 12k $")],
            [KeyboardButton(text="12k - 15k $"), KeyboardButton(text="15k - 20k $")],
            [KeyboardButton(text="20k - 30k $"), KeyboardButton(text="30k+ $")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "📌 <b>4-qadam:</b> Budjetingiz qancha?\n\n"
        "Tanlang yoki o'zingiz yozing:\n"
        "<i>Masalan: 12000-18000</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_budget)


@router.message(BuyRequestStates.waiting_for_budget)
async def process_budget(message: Message, state: FSMContext):
    """Process budget"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    budget_map = {
        "5k - 8k $": (5000, 8000),
        "8k - 12k $": (8000, 12000),
        "12k - 15k $": (12000, 15000),
        "15k - 20k $": (15000, 20000),
        "20k - 30k $": (20000, 30000),
        "30k+ $": (30000, 100000),
    }
    
    if message.text in budget_map:
        budget_min, budget_max = budget_map[message.text]
    elif "-" in message.text:
        try:
            parts = message.text.replace("$", "").replace(" ", "").split("-")
            budget_min = float(parts[0])
            budget_max = float(parts[1])
        except (ValueError, IndexError):
            await message.answer("❌ Noto'g'ri format. Masalan: 12000-18000")
            return
    else:
        try:
            amount = float(message.text.replace("$", "").replace(" ", ""))
            budget_min = amount * 0.8
            budget_max = amount * 1.2
        except ValueError:
            await message.answer("❌ To'g'ri summa kiriting")
            return
    
    await state.update_data(budget_min=budget_min, budget_max=budget_max)
    
    # Transmission
    builder = [[KeyboardButton(text=t)] for t in TRANSMISSIONS]
    builder.append([KeyboardButton(text="❌ Bekor qilish")])
    keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    
    await message.answer(
        "📌 <b>5-qadam:</b> Uzatmalar qutisini tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_transmission)


@router.message(BuyRequestStates.waiting_for_transmission)
async def process_transmission(message: Message, state: FSMContext):
    """Process transmission preference"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    transmission = None if message.text == "Hammasi bo'ladi" else message.text
    await state.update_data(transmission=transmission)
    
    # Notes
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "📌 <b>6-qadam:</b> Qo'shimcha xohishlar\n\n"
        "Masalan:\n"
        "• Rang: oq yoki kumush\n"
        "• Probeg: 50,000 km gacha\n"
        "• Jihozlanishi: lyuk, orqa kamera\n"
        "• Holati: rasmiy dilerdan\n\n"
        "Yoki ⏭ tugmani bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_notes)


@router.message(BuyRequestStates.waiting_for_notes)
async def process_notes(message: Message, state: FSMContext):
    """Process additional notes"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    notes = None if message.text == "O'tkazib yuborish" else message.text
    await state.update_data(additional_notes=notes)
    
    # Phone
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "📌 <b>Oxirgi qadam:</b> Telefon raqamingiz\n\n"
        "Siz bilan tezroq bog'lanishimiz uchun\n"
        "raqamingizni yuboring.\n\n"
        "💡 <i>Telefon yuborsangiz — arizangiz yuqori\n"
        "ustuvorlik oladi va tezroq ko'rib chiqiladi!</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BuyRequestStates.waiting_for_phone)


@router.message(BuyRequestStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Process phone from contact"""
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    
    # Update user phone in DB
    async with async_session_maker() as session:
        from database.crud import update_user_phone
        await update_user_phone(session, message.from_user.id, phone)
    
    await _confirm_buy_request(message, state)


@router.message(BuyRequestStates.waiting_for_phone)
async def process_phone_text(message: Message, state: FSMContext):
    """Process phone from text or skip"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    if message.text == "O'tkazib yuborish":
        await state.update_data(phone=None)
    else:
        await state.update_data(phone=message.text.strip())
    
    await _confirm_buy_request(message, state)


async def _confirm_buy_request(message: Message, state: FSMContext):
    """Show confirmation"""
    data = await state.get_data()
    
    text = (
        "📋 <b>ARIZANGIZ TAYYOR!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    text += f"🏷 Brend: <b>{data.get('brand', '-')}</b>\n"
    text += f"🚙 Model: <b>{data.get('model') or 'Barcha'}</b>\n"
    
    year_from = data.get('year_from')
    year_to = data.get('year_to')
    if year_from and year_to:
        text += f"📅 Yil: <b>{year_from}-{year_to}</b>\n"
    elif year_from:
        text += f"📅 Yil: <b>{year_from}+</b>\n"
    else:
        text += "📅 Yil: <b>Farqi yo'q</b>\n"
    
    budget_min = data.get('budget_min')
    budget_max = data.get('budget_max')
    if budget_min and budget_max:
        text += f"💰 Budjet: <b>{budget_min:,.0f} — {budget_max:,.0f} $</b>\n"
    
    if data.get('transmission'):
        text += f"⚙️ Uzatma: <b>{data['transmission']}</b>\n"
    if data.get('phone'):
        text += f"📞 Telefon: <b>{data['phone']}</b>\n"
    if data.get('additional_notes'):
        text += f"\n📝 Qo'shimcha: <i>{data['additional_notes']}</i>\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "✅ Hamma narsa to'g'rimi? Tasdiqlaysizmi?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="buy_confirm:yes"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="buy_confirm:no")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(BuyRequestStates.confirm_request)


@router.callback_query(F.data == "buy_confirm:no")
async def cancel_buy_request(callback: CallbackQuery, state: FSMContext):
    """Cancel buy request"""
    await state.clear()
    await callback.message.edit_text("❌ Ariza bekor qilindi.")
    await callback.message.answer("Bosh menyu:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "buy_confirm:yes")
async def confirm_buy_request(callback: CallbackQuery, state: FSMContext):
    """Save buy request and notify admin"""
    data = await state.get_data()
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        # Calculate lead score
        user = await get_user_by_id(session, user_id)
        user_lead_score = user.lead_score if user else 0
        
        urgency_detected = detect_urgency_keywords(data.get('additional_notes'))
        
        score, urgency = calculate_inquiry_lead_score(
            has_phone=bool(data.get('phone')),
            has_budget=bool(data.get('budget_min')),
            has_specific_model=bool(data.get('model')),
            is_returning=user and user.total_inquiries > 0,
            urgency_keywords=urgency_detected,
            user_lead_score=user_lead_score
        )
        
        # Create buy request
        buy_request = await create_buy_request(
            session,
            user_id=user_id,
            brand=data.get('brand'),
            model=data.get('model'),
            year_from=data.get('year_from'),
            year_to=data.get('year_to'),
            budget_min=data.get('budget_min'),
            budget_max=data.get('budget_max'),
            transmission=data.get('transmission'),
            additional_notes=data.get('additional_notes'),
            phone=data.get('phone'),
            lead_score=score,
            urgency=urgency
        )
        
        # Update user
        update_data = {}
        if data.get('brand'):
            brands = user.preferred_brands or ""
            if data['brand'].lower() not in brands.lower():
                update_data['preferred_brands'] = f"{brands},{data['brand']}" if brands else data['brand']
        if data.get('budget_min'):
            update_data['budget_min'] = data['budget_min']
        if data.get('budget_max'):
            update_data['budget_max'] = data['budget_max']
        if update_data:
            await update_user_lead_data(session, user_id, **update_data)
        
        # Recalculate user lead score
        await calculate_user_lead_score(session, user_id)
        
        # Schedule follow-ups
        await schedule_followups_for_buy_request(session, buy_request.id, user_id)
        
        # Find matching cars immediately
        matching_cars = await find_matching_cars_for_request(session, buy_request)
    
    await state.clear()
    
    # Respond to user
    response = (
        "✅ <b>ARIZA QABUL QILINDI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Ariza raqami: <b>#{buy_request.id}</b>\n"
        f"🚗 {data.get('brand', '')} {data.get('model', '')}\n\n"
        "Mutaxassislarimiz sizga mos variantlarni\n"
        "qidirib, tez orada xabar beradi.\n\n"
    )
    
    if matching_cars:
        response += f"🎯 <b>Darhol {len(matching_cars)} ta mos variant topildi!</b>\n\n"
        for i, car in enumerate(matching_cars[:3], 1):
            response += (
                f"{i}. <b>{car.brand} {car.model}</b> ({car.year})\n"
                f"   💰 {car.price:,.0f} $ · 🛣 {car.mileage or 0:,} km\n\n"
            )
        if len(matching_cars) > 3:
            response += f"<i>...va yana {len(matching_cars) - 3} ta variant</i>\n\n"
        response += "Batafsil ko'rish uchun 🔍 Qidiruv bo'limiga o'ting.\n"
    else:
        response += (
            "📭 Hozircha bazamizda aniq mos variant topilmadi.\n"
            "Lekin yangi moshina tushishi bilan sizga\n"
            "darhol xabar beriladi! 🔔\n"
        )
    
    response += (
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏰ O'rtacha javob vaqti: <b>1-3 soat</b>\n"
        "📞 Savol bo'lsa: @avtosavdo_admin"
    )
    
    await callback.message.edit_text(response, parse_mode="HTML")
    await callback.message.answer("🏠 <b>Bosh menyu</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
    
    # ====== ADMIN NOTIFICATION ======
    urgency_emoji = get_urgency_emoji(urgency)
    urgency_text = get_urgency_text(urgency)
    score_emoji = get_lead_score_emoji(score)
    
    user_info = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    
    admin_text = (
        f"🛒 <b>YANGI OLISH ARIZASI #{buy_request.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{urgency_emoji} Ustuvorlik: <b>{urgency_text}</b>\n"
        f"{score_emoji} Ball: <b>{score}/100</b>\n\n"
        f"👤 Mijoz: {user_info}\n"
        f"📞 Telefon: {data.get('phone', 'Berilmagan')}\n\n"
        f"🏷 Brend: <b>{data.get('brand', '-')}</b>\n"
        f"🚙 Model: <b>{data.get('model') or 'Barcha'}</b>\n"
    )
    
    if data.get('year_from') and data.get('year_to'):
        admin_text += f"📅 Yil: <b>{data['year_from']}-{data['year_to']}</b>\n"
    
    if data.get('budget_min') and data.get('budget_max'):
        admin_text += f"💰 Budjet: <b>{data['budget_min']:,.0f} - {data['budget_max']:,.0f} $</b>\n"
    
    if data.get('transmission'):
        admin_text += f"⚙️ Uzatma: <b>{data['transmission']}</b>\n"
    if data.get('additional_notes'):
        admin_text += f"\n📝 Qo'shimcha: {data['additional_notes']}\n"
    
    if matching_cars:
        admin_text += f"\n🎯 <b>Bazada {len(matching_cars)} ta mos variant topildi!</b>"
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"buyreq:accept:{buy_request.id}"),
            InlineKeyboardButton(text="📞 Qo'ng'iroq", callback_data=f"buyreq:call:{buy_request.id}")
        ],
        [
            InlineKeyboardButton(text="🔍 Mos variantlar", callback_data=f"buyreq:match:{buy_request.id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"buyreq:reject:{buy_request.id}")
        ]
    ])
    
    # Send to all admins
    bot: Bot = callback.bot
    for admin_id in settings.admin_list:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error notifying admin {admin_id}: {e}")


# ====== ADMIN CALLBACKS FOR BUY REQUESTS ======

@router.callback_query(F.data.startswith("buyreq:accept:"))
async def admin_accept_buy_request(callback: CallbackQuery):
    """Admin accepts buy request"""
    request_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        from database.crud import update_buy_request_status
        await update_buy_request_status(session, request_id, "searching", "Admin qabul qildi")
    
    await callback.answer("✅ Ariza qabul qilindi!")
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ QABUL QILINDI", callback_data="noop")]
        ]
    ))


@router.callback_query(F.data.startswith("buyreq:call:"))
async def admin_call_buy_request(callback: CallbackQuery):
    """Admin marks as called"""
    request_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        request = await get_buy_request_by_id(session, request_id)
        if request:
            await update_buy_request_status(session, request_id, "contacted")
            
            if request.phone:
                await callback.answer(f"📞 Telefon: {request.phone}", show_alert=True)
            else:
                user = await get_user_by_id(session, request.user_id)
                phone = user.phone if user else "Berilmagan"
                await callback.answer(f"📞 Telefon: {phone}", show_alert=True)


@router.callback_query(F.data.startswith("buyreq:match:"))
async def admin_match_buy_request(callback: CallbackQuery):
    """Find matching cars for buy request"""
    request_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        request = await get_buy_request_by_id(session, request_id)
        if not request:
            await callback.answer("❌ Ariza topilmadi", show_alert=True)
            return
        
        matching = await find_matching_cars_for_request(session, request)
    
    if not matching:
        await callback.answer("❌ Mos variant topilmadi", show_alert=True)
        return
    
    text = f"🎯 <b>Ariza #{request_id} uchun mos variantlar:</b>\n\n"
    for i, car in enumerate(matching[:5], 1):
        text += (
            f"{i}. <b>{car.brand} {car.model}</b> ({car.year})\n"
            f"   💰 {car.price:,.0f} $ | Pipeline: {car.pipeline_status}\n\n"
        )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("buyreq:reject:"))
async def admin_reject_buy_request(callback: CallbackQuery):
    """Admin rejects buy request"""
    request_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        from database.crud import update_buy_request_status
        await update_buy_request_status(session, request_id, "rejected", "Admin rad etdi")
    
    await callback.answer("❌ Ariza rad etildi")
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ RAD ETILDI", callback_data="noop")]
        ]
    ))


# ====== MY BUY REQUESTS ======

@router.message(F.text == "📋 Mening arizalarim")
async def show_my_buy_requests(message: Message):
    """Show user's buy requests"""
    user_id = message.from_user.id
    
    async with async_session_maker() as session:
        requests = await get_user_buy_requests(session, user_id)
    
    if not requests:
        await message.answer(
            "📋 <b>MENING ARIZALARIM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Sizda hozircha arizalar yo'q.\n\n"
            "Moshina sotib olish uchun\n"
            "🛒 <b>Moshina olish</b> tugmasini bosing.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    status_emoji = {
        "pending": "⏳",
        "searching": "🔍",
        "found_options": "🎯",
        "contacted": "📞",
        "completed": "✅",
        "rejected": "❌"
    }
    
    text = (
        f"📋 <b>MENING ARIZALARIM</b> ({len(requests)} ta)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for req in requests[:10]:
        emoji = status_emoji.get(req.status, "❓")
        status_labels = {
            "pending": "Kutilmoqda",
            "searching": "Qidirilmoqda",
            "found_options": "Variant topildi",
            "contacted": "Bog'lanildi",
            "completed": "Bajarildi",
            "rejected": "Rad etildi"
        }
        label = status_labels.get(req.status, req.status)
        budget_text = ""
        if req.budget_min and req.budget_max:
            budget_text = f"💰 {req.budget_min:,.0f} — {req.budget_max:,.0f} $"
        text += (
            f"{emoji} <b>#{req.id}</b> — {label}\n"
            f"   🚗 {req.brand or '-'} {req.model or 'Barcha'}\n"
        )
        if budget_text:
            text += f"   {budget_text}\n"
        text += f"   📅 {req.created_at.strftime('%d.%m.%Y')}\n\n"
    
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
