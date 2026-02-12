"""
Favorites handler for user favorite cars
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from loguru import logger

from database.database import async_session_maker
from database.crud import (
    add_to_favorites, remove_from_favorites, 
    get_user_favorites, is_favorite
)
from keyboards.user_keyboards import main_menu_keyboard

router = Router()


@router.callback_query(F.data.startswith("car:favorite:"))
async def toggle_favorite(callback: CallbackQuery):
    """Toggle car in favorites"""
    car_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        # Check if already favorite
        if await is_favorite(session, user_id, car_id):
            # Remove from favorites
            await remove_from_favorites(session, user_id, car_id)
            await callback.answer("❌ Sevimlilardan o'chirildi", show_alert=False)
        else:
            # Add to favorites
            added = await add_to_favorites(session, user_id, car_id)
            if added:
                await callback.answer("❤️ Sevimlilarga qo'shildi!", show_alert=False)
            else:
                await callback.answer("Bu moshina allaqachon sevimlilarda", show_alert=False)


@router.message(F.text == "❤️ Sevimlilar")
async def show_favorites(message: Message):
    """Show user's favorite cars"""
    user_id = message.from_user.id
    
    async with async_session_maker() as session:
        favorites = await get_user_favorites(session, user_id)
    
    if not favorites:
        await message.answer(
            "❌ Sizda hozircha sevimli moshinalar yo'q.\n\n"
            "Moshinani sevimlilarga qo'shish uchun moshina sahifasida ❤️ tugmasini bosing.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    text = "❤️ **Sevimli moshinalar:**\n\n"
    
    for i, car in enumerate(favorites, 1):
        text += f"{i}. {car.brand} {car.model} ({car.year})\n"
        text += f"   💰 <b>{car.price:,.0f} $</b>\n\n"
    
    await message.answer(text, reply_markup=main_menu_keyboard())
    
    # Show first favorite car details
    if favorites:
        car = favorites[0]
        from handlers.catalog import show_car_detail
        await show_car_detail(message, car.id)


async def show_car_detail(message: Message, car_id: int):
    """Show detailed info for a specific car"""
    from database.crud import get_car_by_id, get_car_average_rating, get_car_review_count
    from keyboards.user_keyboards import car_detail_keyboard
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        
        if not car:
            await message.answer("❌ Moshina topilmadi")
            return
        
        rating = await get_car_average_rating(session, car_id)
        review_count = await get_car_review_count(session, car_id)
        
        # Build car description
        color_text = car.color or "Ko'rsatilmagan"
        transmission_text = car.transmission or "Ko'rsatilmagan"
        fuel_text = car.fuel_type or "Ko'rsatilmagan"
        
        text = f"""
🚗 **{car.brand} {car.model}**

📅 Yil: {car.year}
💰 Narxi: <b>{car.price:,.0f} $</b>
🎨 Rang: {color_text}
⚙️ Korobka: {transmission_text}
⛽ Yoqilg'i: {fuel_text}
📏 Probeg: {car.mileage:,} km

{car.description or ''}

⭐ Reyting: {rating:.1f}/5.0 ({review_count} sharh)
👁 Ko'rishlar: {car.views_count}
"""
        
        if car.expert_notes:
            text += f"\n\n📝 **Ekspert xulosasi:**\n{car.expert_notes}"
        
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
