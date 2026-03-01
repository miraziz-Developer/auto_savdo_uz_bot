"""
Subscriptions — Obunalar tizimi
Foydalanuvchi kerakli moshina parametrlarini kiritadi,
yangi e'lon tushganda avtomatik xabar oladi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger

from database.database import async_session_maker
from database.crud import (
    create_subscription, get_user_subscriptions,
    delete_subscription
)
from keyboards.user_keyboards import (
    subscription_keyboard, subscription_item_keyboard,
    cancel_keyboard, main_menu_keyboard, confirm_keyboard
)
from states.states import SubscriptionStates

router = Router()


@router.message(F.text.in_(["🔔 Obuna", "🔔 Obunalar"]))
async def subscription_menu(message: Message):
    """Obunalar bo'limi"""
    text = (
        "🔔 <b>OBUNALAR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sizga kerakli moshina parametrlarini kiriting —\n"
        "tizimga shunday moshina tushishi bilan\n"
        "<b>darhol xabar beramiz!</b> 📩\n\n"
        "📌 <i>Bir nechta obuna yaratishingiz mumkin</i>"
    )
    await message.answer(text, reply_markup=subscription_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "subscription:new")
async def new_subscription(callback: CallbackQuery, state: FSMContext):
    """Yangi obuna yaratish"""
    popular_brands = [
        "Chevrolet", "Hyundai", "Kia", "Toyota",
        "Daewoo", "Nissan", "BMW", "Lada"
    ]
    builder = []
    for i in range(0, len(popular_brands), 2):
        row = [KeyboardButton(text=popular_brands[i])]
        if i + 1 < len(popular_brands):
            row.append(KeyboardButton(text=popular_brands[i+1]))
        builder.append(row)
    builder.append([KeyboardButton(text="❌ Bekor qilish")])
    keyboard = ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True)
    
    await callback.message.answer(
        "🔔 <b>YANGI OBUNA</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏷 <b>Moshina brendini tanlang yoki yozing:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_brand)
    await callback.answer()


@router.message(SubscriptionStates.waiting_for_brand)
async def process_sub_brand(message: Message, state: FSMContext):
    """Brend qabul qilish va narx so'rash (Rapid Flow)"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return
    
    brand = message.text.strip()
    await state.update_data(brand=brand)
    
    # Rapid Flow: Brand -> Price (Skip Model/Year)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="10,000 $"), KeyboardButton(text="15,000 $")],
        [KeyboardButton(text="20,000 $"), KeyboardButton(text="30,000 $")],
        [KeyboardButton(text="50,000 $"), KeyboardButton(text="⏭ Cheklovsiz")],
        [KeyboardButton(text="⚙️ Aniqroq sozlash (Model/Yil)")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ], resize_keyboard=True)
    
    await message.answer(
        f"✅ Brend: <b>{brand}</b>\n\n"
        "💰 <b>Maksimal narxni tanlang:</b>\n"
        "(yoki o'zingiz yozing, masalan: 12500)",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.waiting_for_price_to)


# --- Detailed Flow Handlers (Model & Year) ---

@router.message(SubscriptionStates.waiting_for_model)
async def process_sub_model(message: Message, state: FSMContext):
    """Model qabul qilish (Detailed Flow)"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return
    
    if message.text != "⏭ O'tkazib yuborish":
        await state.update_data(model=message.text.strip())
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="2024"), KeyboardButton(text="2022"), KeyboardButton(text="2020")],
        [KeyboardButton(text="2018"), KeyboardButton(text="2015"), KeyboardButton(text="2010")],
        [KeyboardButton(text="⏭ O'tkazib yuborish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ], resize_keyboard=True)
    
    await message.answer("📅 <b>Minimal yilni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(SubscriptionStates.waiting_for_year_from)


@router.message(SubscriptionStates.waiting_for_year_from)
async def process_sub_year_from(message: Message, state: FSMContext):
    """Yil qabul qilish (Detailed Flow)"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return
    
    if message.text != "⏭ O'tkazib yuborish":
        try:
            year = int(message.text.strip())
            await state.update_data(year_from=year)
        except ValueError:
            await message.answer("❌ Yilni raqamda kiriting.")
            return

    # Ask for price again (completing the circle)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="10,000 $"), KeyboardButton(text="15,000 $")],
        [KeyboardButton(text="20,000 $"), KeyboardButton(text="30,000 $")],
        [KeyboardButton(text="50,000 $"), KeyboardButton(text="⏭ Cheklovsiz")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ], resize_keyboard=True)
    
    await message.answer("💰 <b>Maksimal narxni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(SubscriptionStates.waiting_for_price_to)


@router.message(SubscriptionStates.waiting_for_price_to)
async def process_sub_price_to(message: Message, state: FSMContext):
    """Narx qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    # Check for "More Options" request
    if message.text == "⚙️ Aniqroq sozlash (Model/Yil)":
        # Switch to detailed flow -> Ask Model
        keyboard = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ], resize_keyboard=True)
        await message.answer(
            "🚙 <b>Model nomini kiriting:</b>\n(masalan: Gentra)",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(SubscriptionStates.waiting_for_model)
        return
    
    # Process Price
    price = None
    if message.text != "⏭ Cheklovsiz" and message.text != "⏭ O'tkazib yuborish":
        try:
            price_text = message.text.replace("$", "").replace(",", "").replace(" ", "").strip()
            price = float(price_text)
            await state.update_data(price_to=price)
        except ValueError:
            await message.answer("❌ Narxni to'g'ri kiriting (raqamda).")
            return
            
    # Go straight to Confirmation
    data = await state.get_data()
    # Ensure optional fields are None if skipped in rapid flow
    if 'model' not in data: await state.update_data(model=None)
    if 'year_from' not in data: await state.update_data(year_from=None)
    
    # Re-fetch data
    data = await state.get_data()
    
    text = "📋 <b>OBUNA TASDIQLASH</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += f"🏷 Brend: <b>{data.get('brand')}</b>\n"
    if data.get('model'): text += f"🚙 Model: <b>{data['model']}</b>\n"
    if data.get('year_from'): text += f"📅 Yil: <b>{data['year_from']}+</b>\n"
    
    if data.get('price_to'):
        text += f"💰 Narx: <b>{data['price_to']:,.0f} $</b> gacha\n"
    else:
        text += f"💰 Narx: <b>Cheklovsiz</b>\n"
    
    text += "\n✅ Shu parametrlarga mos yangi e'lon chiqqanda xabar beramiz!"
    
    await message.answer(
        text,
        reply_markup=confirm_keyboard("subscription"),
        parse_mode="HTML"
    )
    await state.set_state(SubscriptionStates.confirm_subscription)


@router.callback_query(F.data == "confirm:subscription", SubscriptionStates.confirm_subscription)
async def confirm_subscription(callback: CallbackQuery, state: FSMContext):
    """Obunani tasdiqlash va saqlash"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        from database.crud import get_or_create_user
        await get_or_create_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        subscription = await create_subscription(
            session,
            user_id=callback.from_user.id,
            brand=data.get('brand'),
            model=data.get('model'),
            year_from=data.get('year_from'),
            price_to=data.get('price_to')
        )
    
    await state.clear()
    
    text = (
        "✅ <b>Obuna muvaffaqiyatli yaratildi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if data.get('brand'):
        text += f"🏷 {data['brand']}"
    if data.get('model'):
        text += f" {data['model']}"
    if data.get('year_from'):
        text += f" ({data['year_from']}+)"
    if data.get('price_to'):
        text += f" — {data['price_to']:,.0f}$ gacha"
    
    text += (
        "\n\n📩 Shu parametrlarga mos yangi e'lon chiqqanda\n"
        "sizga <b>darhol xabar yuboriladi</b>.\n\n"
        "🔔 Obunalaringizni boshqarish uchun\n"
        "<b>🔔 Obunalar</b> bo'limiga o'ting."
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.message.answer("🏠 Bosh menyu:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "cancel:subscription")
async def cancel_subscription_creation(callback: CallbackQuery, state: FSMContext):
    """Obuna yaratishni bekor qilish"""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Obuna yaratish bekor qilindi</b>",
        parse_mode="HTML"
    )
    await callback.message.answer("🏠 Bosh menyu:", reply_markup=main_menu_keyboard())


@router.message(F.text == "📊 Mening obunalarim")
@router.callback_query(F.data == "subscription:list")
async def list_subscriptions(event, state: FSMContext):
    """Obunalar ro'yxati"""
    user_id = event.from_user.id
    
    async with async_session_maker() as session:
        subscriptions = await get_user_subscriptions(session, user_id)
    
    if not subscriptions:
        text = (
            "🔔 <b>Sizda hozircha obunalar yo'q</b>\n\n"
            "Yangi obuna yaratish uchun quyidagi tugmani bosing.\n"
            "Sizga kerakli moshina parametrlarini kiritsangiz,\n"
            "yangi e'lon chiqqanda darhol xabar beramiz!"
        )
        
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=subscription_keyboard(), parse_mode="HTML")
        else:
            await event.answer(text, reply_markup=subscription_keyboard(), parse_mode="HTML")
        return
    
    text = f"🔔 <b>MENING OBUNALARIM</b> ({len(subscriptions)} ta)\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, sub in enumerate(subscriptions, 1):
        text += f"{i}. "
        if sub.brand:
            text += f"🏷 <b>{sub.brand}</b> "
        if sub.model:
            text += f"{sub.model} "
        if sub.year_from:
            text += f"({sub.year_from}+) "
        if sub.price_to:
            text += f"— <b>{sub.price_to:,.0f} $</b> gacha"
        text += "\n"
    
    text += "\nO'chirish uchun quyidagi tugmalarni bosing 👇"
    
    # Build delete buttons
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for sub in subscriptions:
        label = sub.brand or ""
        if sub.model:
            label += f" {sub.model}"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {label.strip()}",
                callback_data=f"subscription:delete:{sub.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Yangi obuna", callback_data="subscription:new")])
    buttons.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("subscription:delete:"))
async def delete_subscription_handler(callback: CallbackQuery):
    """Obunani o'chirish"""
    subscription_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        await delete_subscription(session, subscription_id)
    
    await callback.answer("✅ Obuna o'chirildi", show_alert=True)
    await list_subscriptions(callback, None)
