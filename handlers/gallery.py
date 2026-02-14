"""
Gallery — Moshina rasmlarini ko'rish
Media-group shaklida barcha rasmlarni yuboradi
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from loguru import logger

from database.database import async_session_maker
from database.crud import get_car_by_id

router = Router()


@router.callback_query(F.data.startswith("car:gallery:"))
async def show_car_gallery(callback: CallbackQuery):
    """Moshina rasmlar galereyasi"""
    car_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        
        if not car:
            await callback.answer("❌ Moshina topilmadi", show_alert=True)
            return
        
        if not car.images:
            await callback.answer(
                "📷 Bu moshina uchun rasmlar mavjud emas",
                show_alert=True
            )
            return
        
        if isinstance(car.images, dict):
            image_urls = []
            
            if 'main' in car.images and car.images['main']:
                image_urls.append(car.images['main'])
            
            if 'gallery' in car.images and isinstance(car.images['gallery'], list):
                image_urls.extend(car.images['gallery'])
            
            if not image_urls:
                await callback.answer(
                    "📷 Rasmlar topilmadi",
                    show_alert=True
                )
                return
            
            if len(image_urls) > 1:
                media_group = []
                for i, url in enumerate(image_urls[:10]):
                    if i == 0:
                        caption = (
                            f"📸 <b>{car.brand} {car.model}</b> ({car.year})\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"Jami: {len(image_urls)} ta rasm\n"
                            f"💰 Narxi: {car.price:,.0f} $"
                        )
                    else:
                        caption = None
                    
                    media_group.append(InputMediaPhoto(
                        media=url,
                        caption=caption,
                        parse_mode="HTML" if caption else None
                    ))
                
                try:
                    await callback.message.answer_media_group(media_group)
                    await callback.answer(f"📸 {len(image_urls)} ta rasm yuborildi")
                except Exception as e:
                    logger.error(f"Gallery error: {e}")
                    await callback.answer(
                        "❌ Rasmlarni yuborishda xatolik yuz berdi",
                        show_alert=True
                    )
            else:
                try:
                    await callback.message.answer_photo(
                        photo=image_urls[0],
                        caption=(
                            f"📸 <b>{car.brand} {car.model}</b> ({car.year})\n"
                            f"💰 Narxi: {car.price:,.0f} $"
                        ),
                        parse_mode="HTML"
                    )
                    await callback.answer()
                except Exception as e:
                    logger.error(f"Photo error: {e}")
                    await callback.answer(
                        "❌ Rasmni yuborishda xatolik",
                        show_alert=True
                    )
        else:
            await callback.answer(
                "❌ Rasm formati noto'g'ri",
                show_alert=True
            )
