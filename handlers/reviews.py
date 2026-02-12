"""
Reviews handler for car reviews and ratings
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
    """Review states"""
    waiting_for_rating = State()
    waiting_for_comment = State()


@router.callback_query(F.data.startswith("car:review:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    """Start review process"""
    car_id = int(callback.data.split(":")[2])
    
    await state.update_data(car_id=car_id)
    
    # Create rating keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="rating:1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rating:2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating:3"),
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating:4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating:5"),
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="review:cancel")
        ]
    ])
    
    await callback.message.edit_text(
        "⭐ **Bahoni tanlang:**\n\n"
        "1 yulduz - Juda yomon\n"
        "2 yulduz - Yomon\n"
        "3 yulduz - O'rtacha\n"
        "4 yulduz - Yaxshi\n"
        "5 yulduz - A'lo!",
        reply_markup=keyboard
    )
    await state.set_state(ReviewStates.waiting_for_rating)


@router.callback_query(F.data.startswith("rating:"), ReviewStates.waiting_for_rating)
async def process_rating(callback: CallbackQuery, state: FSMContext):
    """Process rating selection"""
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)
    
    stars = "⭐" * rating
    await callback.message.edit_text(
        f"Siz {stars} ({rating}/5) tanladingiz.\n\n"
        "Fikr-mulohazangizni yozing yoki /skip tugmasini bosing:"
    )
    await state.set_state(ReviewStates.waiting_for_comment)


@router.message(ReviewStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Process review comment"""
    data = await state.get_data()
    car_id = data['car_id']
    rating = data['rating']
    comment = None if message.text == "/skip" else message.text
    
    # Save review
    async with async_session_maker() as session:
        await create_review(
            session,
            user_id=message.from_user.id,
            car_id=car_id,
            rating=rating,
            comment=comment
        )
    
    await state.clear()
    
    stars = "⭐" * rating
    await message.answer(
        f"✅ Rahmat! Sizning bahongiz saqlandi.\n\n{stars} ({rating}/5)",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("car:reviews:"))
async def show_car_reviews(callback: CallbackQuery):
    """Show all reviews for a car"""
    car_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        reviews = await get_car_reviews(session, car_id)
        avg_rating = await get_car_average_rating(session, car_id)
    
    if not reviews:
        await callback.answer(
            "Bu moshina haqida hali sharhlar yo'q",
            show_alert=True
        )
        return
    
    text = f"⭐ **O'rtacha baho: {avg_rating:.1f}/5.0**\n"
    text += f"📊 Jami sharhlar: {len(reviews)}\n\n"
    text += "---\n\n"
    
    for review in reviews[:10]:  # Show max 10 reviews
        stars = "⭐" * review['rating']
        text += f"{stars} ({review['rating']}/5)\n"
        text += f"👤 {review['user_name']}\n"
        
        if review['comment']:
            text += f"💬 {review['comment']}\n"
        
        date_str = review['created_at'].strftime('%d.%m.%Y')
        text += f"📅 {date_str}\n\n"
    
    if len(reviews) > 10:
        text += f"\n... va yana {len(reviews) - 10} ta sharh"
    
    await callback.message.answer(text)


@router.callback_query(F.data == "review:cancel")
async def cancel_review(callback: CallbackQuery, state: FSMContext):
    """Cancel review"""
    await state.clear()
    await callback.message.edit_text("❌ Sharh yozish bekor qilindi")
