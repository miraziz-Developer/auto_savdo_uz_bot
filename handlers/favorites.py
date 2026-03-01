"""
Favorites — Sevimlilar ro'yxati
Foydalanuvchi yoqtirgan moshinalarni saqlab qo'yadi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from database.database import async_session_maker
from database.crud import (
    add_to_favorites, remove_from_favorites,
    get_user_favorites, is_favorite
)
from keyboards.user_keyboards import main_menu_keyboard, car_detail_keyboard

router = Router()


@router.callback_query(F.data.startswith("car:favorite:"))
async def toggle_favorite(callback: CallbackQuery):
    """Sevimlilardan qo'shish/o'chirish"""
    car_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        from database.crud import get_or_create_user
        await get_or_create_user(
            session,
            telegram_id=user_id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        if await is_favorite(session, user_id, car_id):
            await remove_from_favorites(session, user_id, car_id)
            await callback.answer("💔 Sevimlilardan o'chirildi", show_alert=False)
        else:
            added = await add_to_favorites(session, user_id, car_id)
            if added:
                await callback.answer("❤️ Sevimlilarga qo'shildi!", show_alert=False)
            else:
                await callback.answer("Allaqachon sevimlilarda", show_alert=False)


@router.message(F.text == "❤️ Sevimlilar")
async def show_favorites(message: Message):
    """Sevimli moshinalar ro'yxati"""
    user_id = message.from_user.id
    
    async with async_session_maker() as session:
        favorites = await get_user_favorites(session, user_id)
    
    if not favorites:
        await message.answer(
            "❤️ <b>SEVIMLILAR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Hozircha sevimli moshinalaringiz yo'q.\n\n"
            "Moshina sahifasidagi ❤️ tugmasini bosib\n"
            "sevimlilarga qo'shing — keyinroq tez topasiz!",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = f"❤️ <b>SEVIMLI MOSHINALAR</b> ({len(favorites)} ta)\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    buttons = []
    for i, car in enumerate(favorites, 1):
        avail = "✅" if car.is_available else "❌ Sotilgan"
        text += (
            f"{i}. <b>{car.brand} {car.model}</b> ({car.year})\n"
            f"   💰 {car.price:,.0f} $ — {avail}\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"👁 {car.brand} {car.model}",
                callback_data=f"fav:view:{car.id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"fav:remove:{car.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("fav:view:"))
async def view_favorite_car(callback: CallbackQuery):
    """Sevimli moshinani ko'rish"""
    car_id = int(callback.data.split(":")[2])
    await show_car_detail(callback.message, car_id)
    await callback.answer()


@router.callback_query(F.data.startswith("fav:remove:"))
async def remove_favorite(callback: CallbackQuery):
    """Sevimlilardan o'chirish"""
    car_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        await remove_from_favorites(session, callback.from_user.id, car_id)
    
    await callback.answer("💔 O'chirildi", show_alert=True)
    # Refresh list
    await show_favorites(callback.message)


async def show_car_detail(message: Message, car_id: int):
    """Moshina tafsilotlarini ko'rsatish"""
    from database.crud import get_car_by_id, get_car_average_rating, get_car_review_count
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        
        if not car:
            await message.answer(
                "❌ <b>Moshina topilmadi</b>\n"
                "E'lon olib tashlangan bo'lishi mumkin.",
                parse_mode="HTML"
            )
            return
        
        rating = await get_car_average_rating(session, car_id)
        review_count = await get_car_review_count(session, car_id)
        
        color_text = car.color or "ko'rsatilmagan"
        transmission_text = car.transmission or "ko'rsatilmagan"
        fuel_text = car.fuel_type or "ko'rsatilmagan"
        mileage_text = f"{car.mileage:,} km" if car.mileage else "ko'rsatilmagan"
        
        # Rating stars
        if rating > 0:
            full_stars = int(rating)
            stars = "⭐" * full_stars
            rating_text = f"{stars} {rating:.1f}/5 ({review_count} sharh)"
        else:
            rating_text = "Hali baholanmagan"
        
        avail_text = "✅ Mavjud" if car.is_available else "❌ Sotilgan"
        
        text = (
            f"🚗 <b>{car.brand} {car.model}</b> ({car.year})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Narxi: <b>{car.price:,.0f} $</b>\n"
            f"📊 Holat: {avail_text}\n\n"
            f"📅 Yili: <b>{car.year}</b>\n"
            f"🛣 Probegi: <b>{mileage_text}</b>\n"
            f"⚙️ Uzatma: <b>{transmission_text}</b>\n"
            f"⛽ Yoqilg'i: <b>{fuel_text}</b>\n"
            f"🎨 Rangi: <b>{color_text}</b>\n\n"
            f"⭐ Reyting: {rating_text}\n"
            f"👁 Ko'rishlar: {car.views_count}\n"
        )
        
        if car.description:
            desc = car.description[:300]
            if len(car.description) > 300:
                desc += "..."
            text += f"\n📝 <b>Tavsif:</b>\n<i>{desc}</i>\n"
        
        if car.expert_notes:
            text += f"\n💎 <b>Ekspert bahosi:</b>\n<i>{car.expert_notes}</i>\n"
        
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
