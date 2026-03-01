"""
Reviews — Sharhlar va baholash
Foydalanuvchi moshinaga baho beradi (1-5 yulduz + izoh)
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from database.database import async_session_maker
from database.crud import (
    create_review, get_car_reviews,
    get_car_average_rating, get_car_review_count
)
from keyboards.user_keyboards import cancel_keyboard, main_menu_keyboard

router = Router()


class ReviewStates(StatesGroup):
    """Sharh yozish bosqichlari"""
    waiting_for_rating = State()
    waiting_for_comment = State()


@router.callback_query(F.data.startswith("car:review:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    """Sharh yozishni boshlash"""
    car_id = int(callback.data.split(":")[2])
    await state.update_data(car_id=car_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 ⭐", callback_data="rating:1"),
            InlineKeyboardButton(text="2 ⭐", callback_data="rating:2"),
            InlineKeyboardButton(text="3 ⭐", callback_data="rating:3"),
        ],
        [
            InlineKeyboardButton(text="4 ⭐", callback_data="rating:4"),
            InlineKeyboardButton(text="5 ⭐", callback_data="rating:5"),
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="review:cancel")
        ]
    ])
    
    await callback.message.edit_text(
        "⭐ <b>BAHO BERING</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Ushbu moshinaga 1 dan 5 gacha baho bering:\n\n"
        "1 ⭐ — Yoqmadi\n"
        "2 ⭐ — O'rtacha past\n"
        "3 ⭐ — O'rtacha\n"
        "4 ⭐ — Yaxshi\n"
        "5 ⭐ — Ajoyib!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(ReviewStates.waiting_for_rating)


@router.callback_query(F.data.startswith("rating:"), ReviewStates.waiting_for_rating)
async def process_rating(callback: CallbackQuery, state: FSMContext):
    """Baho qabul qilish"""
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)
    
    stars = "⭐" * rating
    
    await callback.message.edit_text(
        f"✅ Baho: {stars} ({rating}/5)\n\n"
        "💬 <b>Fikringizni yozing:</b>\n\n"
        "<i>Bu moshina haqida nima deyishingiz mumkin?\n"
        "Yoki /skip yozib o'tkazib yuboring.</i>",
        parse_mode="HTML"
    )
    await state.set_state(ReviewStates.waiting_for_comment)


@router.message(ReviewStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Izoh qabul qilish"""
    data = await state.get_data()
    car_id = data['car_id']
    rating = data['rating']
    comment = None if message.text == "/skip" else message.text
    
    async with async_session_maker() as session:
        from database.crud import get_or_create_user
        await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        await create_review(
            session,
            user_id=message.from_user.id,
            car_id=car_id,
            rating=rating,
            comment=comment
        )
    
    await state.clear()
    
    stars = "⭐" * rating
    
    text = (
        "✅ <b>Rahmat, bahoyingiz saqlandi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Sizning bahoyingiz: {stars} ({rating}/5)\n"
    )
    if comment:
        text += f'💬 Izoh: "<i>{comment}</i>"\n'
    
    text += "\nBoshqa foydalanuvchilarga yordam berasiz! 🙏"
    
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("car:reviews:"))
async def show_car_reviews(callback: CallbackQuery):
    """Moshinaning barcha sharhlari"""
    car_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        reviews = await get_car_reviews(session, car_id)
        avg_rating = await get_car_average_rating(session, car_id)
    
    if not reviews:
        await callback.answer(
            "Bu moshina haqida hali sharhlar yo'q.\nBirinchi bo'lib baho bering!",
            show_alert=True
        )
        return
    
    full_stars = int(avg_rating)
    stars_display = "⭐" * full_stars
    
    text = (
        f"📊 <b>SHARHLAR</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"O'rtacha baho: {stars_display} <b>{avg_rating:.1f}/5.0</b>\n"
        f"Jami sharhlar: <b>{len(reviews)}</b> ta\n\n"
    )
    
    for review in reviews[:10]:
        r_stars = "⭐" * review['rating']
        text += f"{'─' * 20}\n"
        text += f"{r_stars} ({review['rating']}/5)\n"
        text += f"👤 {review['user_name']}\n"
        
        if review['comment']:
            comment = review['comment'][:150]
            if len(review['comment']) > 150:
                comment += "..."
            text += f'💬 "<i>{comment}</i>"\n'
        
        date_str = review['created_at'].strftime('%d.%m.%Y')
        text += f"📅 {date_str}\n\n"
    
    if len(reviews) > 10:
        text += f"\n<i>...va yana {len(reviews) - 10} ta sharh</i>"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "review:cancel")
async def cancel_review(callback: CallbackQuery, state: FSMContext):
    """Sharhni bekor qilish"""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Sharh yozish bekor qilindi</b>",
        parse_mode="HTML"
    )
