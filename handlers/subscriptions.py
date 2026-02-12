"""
Subscription handlers for car alerts
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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


@router.message(F.text == "🔔 Obuna")
async def subscription_menu(message: Message):
    """Subscription menu"""
    text = """
 🔔 **Moshina qidirish (Obuna)**

Siz o'zingizga kerakli moshinaning parametrlarini kiritasiz.
Tizimga shunday moshina tushishi bilan sizga darhol xabar beramiz! 

Quyidagi tugmalardan birini tanlang:
"""
    await message.answer(text, reply_markup=subscription_keyboard())


@router.callback_query(F.data == "subscription:new")
async def new_subscription(callback: CallbackQuery, state: FSMContext):
    """Start creating new subscription"""
    await callback.message.edit_text(
        "🔔 **Yangi obuna yaratish**\n\n"
        "Moshina brendini kiriting (masalan: Chevrolet)\n\n"
        "Bekor qilish uchun /cancel yozing"
    )
    await state.set_state(SubscriptionStates.waiting_for_brand)


@router.message(SubscriptionStates.waiting_for_brand)
async def process_sub_brand(message: Message, state: FSMContext):
    """Process subscription brand"""
    await state.update_data(brand=message.text)
    await message.answer(
        "Model nomini kiriting (masalan: Gentra)\n\n"
        "Yoki /skip yozib o'tkazib yuboring"
    )
    await state.set_state(SubscriptionStates.waiting_for_model)


@router.message(SubscriptionStates.waiting_for_model)
async def process_sub_model(message: Message, state: FSMContext):
    """Process subscription model"""
    if message.text != "/skip":
        await state.update_data(model=message.text)
    
    await message.answer(
        "Minimal yilni kiriting (masalan: 2020)\n\n"
        "Yoki /skip yozib o'tkazib yuboring"
    )
    await state.set_state(SubscriptionStates.waiting_for_year_from)


@router.message(SubscriptionStates.waiting_for_year_from)
async def process_sub_year_from(message: Message, state: FSMContext):
    """Process subscription year from"""
    if message.text != "/skip":
        try:
            year = int(message.text)
            await state.update_data(year_from=year)
        except ValueError:
            await message.answer("❌ Iltimos, to'g'ri yil kiriting")
            return
    
    await message.answer(
        "Maksimal narxni kiriting (masalan: 150000000)\n\n"
        "Yoki /skip yozib o'tkazib yuboring"
    )
    await state.set_state(SubscriptionStates.waiting_for_price_to)


@router.message(SubscriptionStates.waiting_for_price_to)
async def process_sub_price_to(message: Message, state: FSMContext):
    """Process subscription price to"""
    if message.text != "/skip":
        try:
            price = float(message.text.replace(" ", "").replace(",", ""))
            await state.update_data(price_to=price)
        except ValueError:
            await message.answer("❌ Iltimos, to'g'ri narx kiriting")
            return
    
    # Show confirmation
    data = await state.get_data()
    
    confirm_text = "✅ **Obuna tasdigi**\n\n"
    if data.get('brand'):
        confirm_text += f"🏷 Brend: {data['brand']}\n"
    if data.get('model'):
        confirm_text += f"🚙 Model: {data['model']}\n"
    if data.get('year_from'):
        confirm_text += f"📅 Minimal yil: {data['year_from']}\n"
    if data.get('price_to'):
        confirm_text += f"💰 Maksimal narx: <b>{data['price_to']:,.0f} $</b>\n"
    
    confirm_text += "\n\nTasdiqlaysizmi?"
    
    await message.answer(confirm_text, reply_markup=confirm_keyboard("subscription"))
    await state.set_state(SubscriptionStates.confirm_subscription)


@router.callback_query(F.data == "confirm:subscription", SubscriptionStates.confirm_subscription)
async def confirm_subscription(callback: CallbackQuery, state: FSMContext):
    """Confirm and save subscription"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        subscription = await create_subscription(
            session,
            user_id=callback.from_user.id,
            brand=data.get('brand'),
            model=data.get('model'),
            year_from=data.get('year_from'),
            price_to=data.get('price_to')
        )
    
    await state.clear()
    await callback.message.edit_text(
        "✅ Obuna muvaffaqiyatli yaratildi!\n\n"
        "Sizning kriteriyalaringizga mos moshina paydo bo'lganda "
        "darhol xabar beramiz! 🔔"
    )
    await callback.message.answer(
        "Bosh menyuga qaytish:",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "cancel:subscription")
async def cancel_subscription_creation(callback: CallbackQuery, state: FSMContext):
    """Cancel subscription creation"""
    await state.clear()
    await callback.message.edit_text("❌ Obuna yaratish bekor qilindi")
    await callback.message.answer(
        "Bosh menyu:",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "📊 Mening obunalarim")
@router.callback_query(F.data == "subscription:list")
async def list_subscriptions(event, state: FSMContext):
    """List user subscriptions"""
    # Handle both Message and CallbackQuery
    user_id = event.from_user.id
    
    async with async_session_maker() as session:
        subscriptions = await get_user_subscriptions(session, user_id)
    
    if not subscriptions:
        text = "❌ Sizda hozircha obunalar yo'q.\n\nYangi obuna yaratish uchun 🔔 Obuna tugmasini bosing."
        
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=subscription_keyboard())
        else:
            await event.answer(text, reply_markup=subscription_keyboard())
        return
    
    text = "📋 **Sizning obunalaringiz:**\n\n"
    
    for i, sub in enumerate(subscriptions, 1):
        text += f"{i}. "
        if sub.brand:
            text += f"{sub.brand} "
        if sub.model:
            text += f"{sub.model} "
        if sub.year_from:
            text += f"({sub.year_from}+) "
        if sub.price_to:
            text += f"- <b>{sub.price_to:,.0f} $</b> gacha"
        text += f"\n   ID: {sub.id}\n\n"
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text)
        # Show delete options for first subscription
        if subscriptions:
            await event.message.answer(
                "O'chirish uchun obuna ID sini yuboring:",
                reply_markup=subscription_item_keyboard(subscriptions[0].id)
            )
    else:
        await event.answer(text)


@router.callback_query(F.data.startswith("subscription:delete:"))
async def delete_subscription_handler(callback: CallbackQuery):
    """Delete subscription"""
    subscription_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        await delete_subscription(session, subscription_id)
    
    await callback.answer("✅ Obuna o'chirildi", show_alert=True)
    await list_subscriptions(callback, None)
