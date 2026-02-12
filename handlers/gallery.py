"""
Image gallery handler for car images
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from loguru import logger

from database.database import async_session_maker
from database.crud import get_car_by_id

router = Router()


@router.callback_query(F.data.startswith("car:gallery:"))
async def show_car_gallery(callback: CallbackQuery):
    """Show car image gallery"""
    car_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        
        if not car:
            await callback.answer("❌ Moshina topilmadi", show_alert=True)
            return
        
        if not car.images:
            await callback.answer(
                "❌ Bu moshina uchun rasmlar mavjud emas",
                show_alert=True
            )
            return
        
        # If images is a dict with multiple images
        if isinstance(car.images, dict):
            image_urls = []
            
            # Collect all image URLs
            if 'main' in car.images and car.images['main']:
                image_urls.append(car.images['main'])
            
            if 'gallery' in car.images and isinstance(car.images['gallery'], list):
                image_urls.extend(car.images['gallery'])
            
            if not image_urls:
                await callback.answer(
                    "❌ Rasmlar topilmadi",
                    show_alert=True
                )
                return
            
            # Send as media group if multiple images
            if len(image_urls) > 1:
                media_group = []
                for i, url in enumerate(image_urls[:10]):  # Max 10 images
                    if i == 0:
                        caption = f"🖼 {car.brand} {car.model} ({car.year})\n\n{len(image_urls)} ta rasm"
                    else:
                        caption = None
                    
                    media_group.append(InputMediaPhoto(media=url, caption=caption))
                
                try:
                    await callback.message.answer_media_group(media_group)
                    await callback.answer("✅ Rasmlar yuborildi")
                except Exception as e:
                    logger.error(f"Error sending gallery: {e}")
                    await callback.answer(
                        "❌ Rasmlarni yuborishda xatolik",
                        show_alert=True
                    )
            else:
                # Single image
                try:
                    await callback.message.answer_photo(
                        photo=image_urls[0],
                        caption=f"🖼 {car.brand} {car.model} ({car.year})"
                    )
                    await callback.answer()
                except Exception as e:
                    logger.error(f"Error sending image: {e}")
                    await callback.answer(
                        "❌ Rasmni yuborishda xatolik",
                        show_alert=True
                    )
        else:
            await callback.answer(
                "❌ Noto'g'ri rasm formati",
                show_alert=True
            )
