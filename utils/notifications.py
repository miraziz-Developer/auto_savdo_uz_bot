"""
Utility functions for sending notifications
"""
from typing import List, Dict
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from config import settings

# Global bot instance
bot = None

LIQUIDITY_MAP = {
    'gentra': '🔥 Juda tez (1-3 kun)',
    'cobalt': '🔥 Juda tez (1-3 kun)',
    'spark': '🚀 Tez (2-5 kun)',
    'nexia': '🚀 Tez (3-5 kun)',
    'damas': '🔥 Juda tez (1-2 kun)',
    'matiz': '🚀 Tez (3-7 kun)',
    'malibu': '⚠️ O\'rtacha (10-20 kun)',
    'tracker': '⚠️ O\'rtacha (7-15 kun)',
    'onix': '⚠️ O\'rtacha (7-15 kun)',
    'kia': '🐢 Sekin (20+ kun)',
    'hyundai': '🐢 Sekin (20+ kun)',
    'byd': '🚀 Tezlashmoqda (5-10 kun)',
    'chery': '🐢 Sekin (30+ kun)',
    'jetour': '🐢 Sekin (30+ kun)',
}


def set_bot_instance(bot_instance: Bot):
    """Set global bot instance"""
    global bot
    bot = bot_instance


async def notify_subscribers_about_car(user_id: int, listing_data: Dict):
    """
    Notify subscriber about matching car
    """
    try:
        brand = listing_data.get('brand') or "Noma'lum"
        model = listing_data.get('model') or "Noma'lum"
        year = listing_data.get('year') or "Noma'lum"
        price = listing_data.get('price', 0)
        source = listing_data.get('source', '').upper()
        
        text = f"""
💎 <b>YANGI E'LON TOPILDI!</b>

🚗 <b>{brand} {model}</b>
📅 Yili: <b>{year}</b>
💵 Narxi: <b>{price:,.0f} $</b>

🌐 Manba: <b>{source}</b>

✨ <i>Ushbu avtomobil sizning qidiruvingizga mos keladi.</i>
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Batafsil ko'rish", url=listing_data.get('url', ''))]
        ])
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Notification sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")


async def send_push_notification(user_id: int, cars: List):
    """
    Send weekly push notification with top cars
    """
    try:
        text = "🚀 <b>HAFTALIK TOP TAKLIFLAR!</b>\n\n"
        
        for i, car in enumerate(cars, 1):
            text += f"{i}. <b>{car.brand} {car.model}</b> ({car.year}) — <b>{car.price:,.0f} $</b>\n"
        
        text += "\n📍 <i>Eng yaxshi takliflarni o'tkazib yubormang!</i>"
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error sending push notification to user {user_id}: {e}")


async def notify_admin_about_good_deal(listing_data: Dict):
    """
    Notify admins about good deals from scraped listings
    """
    try:
        text = f"""
💰 <b>ARZON VARIANT (SHOSHILINCH!)</b>

🚗 <b>{listing_data.get('title', '')}</b>
💵 Narxi: <b>{listing_data.get('price', 0):,.0f} $</b>
🌐 Manba: <b>{listing_data.get('source', '').upper()}</b>

🚀 <i>Bu narx bozor qiymatidan sezilarli darajada past!</i>
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 E'lonni ochish", url=listing_data.get('url', ''))]
        ])
        
        for admin_id in settings.admin_list:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending to admin {admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error sending good deal notification: {e}")


async def publish_scraped_deal(listing_data: Dict):
    """
    Publish scraped car deal to specific channel
    """
    try:
        source = listing_data.get('source', '').upper()
        url = listing_data.get('url', '#')
        
        brand = listing_data.get('brand') or "Noma'lum"
        model = listing_data.get('model') or "Noma'lum"
        year = listing_data.get('year') or "Noma'lum"
        price = listing_data.get('price', 0)
        location = listing_data.get('location', "Noma'lum")
        mileage = listing_data.get('mileage', 0)
        transmission = listing_data.get('transmission', "Noma'lum")
        fuel_type = listing_data.get('fuel_type', "Noma'lum")
        description = (listing_data.get('description') or "").lower()
        
        # Keyword Analysis
        urgency_tag = ""
        if any(w in description for w in ['srochno', 'zarur', 'tez sotiladi', 'pul kerak', 'kami bor']):
            urgency_tag = "🔥 <b>SROCHNO!</b> "
        if any(w in description for w in ['naqd', 'faqat naqd']):
            urgency_tag += "💵 <b>NAQDGA!</b>"
            
        condition_tag = ""
        if any(w in description for w in ['toza', 'kraska yo\'q', 'petno yo\'q', 'radnoy']):
            condition_tag = "✨ <b>HOLATI: TOZA</b>"
        elif 'kraska bor' in description or 'dtp' in description or 'petno' in description:
            condition_tag = "⚠️ <b>HOLATI: Kraska/Petno bor</b>"
            
        owner_tag = ""
        if any(w in description for w in ['ozimniki', 'o\'zimniki', 'tirikchilik emas', 'salondan']):
            owner_tag = "👨‍💼 <b>EGASIDAN</b>"
            
        credit_tag = ""
        if any(w in description for w in ['variant', 'ijara', 'boshiga', 'oyiga', 'vikup']):
            credit_tag = "💳 <b>VARIANT/KREDIT</b>"
        
        # Market Analysis
        avg_price = listing_data.get('avg_price', 0)
        is_good_deal = listing_data.get('is_good_deal', False)
        is_price_drop = listing_data.get('is_price_drop', False)
        
        deal_tag = ""
        profit_text = ""
        
        if is_price_drop:
            old_price = listing_data.get('old_price', 0)
            diff = listing_data.get('price_diff', 0)
            deal_tag = f"\n📉 <b>NARX TUSHDI! (-{diff:,.0f} $)</b>"
            price_display = f"<s>{old_price:,.0f} $</s> ➡️ <b>{price:,.0f} $</b>"
        else:
            price_display = f"<b>{price:,.0f} $</b>"
            
        if is_good_deal:
            diff = avg_price - price
            percent = (diff / avg_price) * 100 if avg_price else 0
            
            if not deal_tag: 
                deal_tag = f"\n🤑 <b>SUPER DEAL! (BOZORDAN {percent:.0f}% ARZON)</b>"
            
            profit_text = f"\n📉 <b>O'rtacha narx:</b> ~{avg_price:,.0f} $\n💰 <b>Potentsial foyda:</b> ~{diff:,.0f} $"

        # Market Analysis Data
        competitors = listing_data.get('competitor_count', 0)
        comp_text = f"{competitors} ta"
        if competitors < 3: comp_text += " (OZ QOLGAN!)"
        elif competitors > 20: comp_text += " (Ko'p)"
        
        liquidity = "Noma'lum"
        if model.lower() in LIQUIDITY_MAP:
            liquidity = LIQUIDITY_MAP[model.lower()]
        else:
            # Try partial match
            for k, v in LIQUIDITY_MAP.items():
                if k in model.lower() or k in brand.lower():
                    liquidity = v
                    break

        market_context = f"""
📊 <b>BOZOR TAHLILI:</b>
📉 Raqobatchilar: <b>{comp_text}</b>
⏳ Sotilish tezligi: <b>{liquidity}</b>
"""

        text = f"""
{deal_tag}
🔥 <b>YANGI TAKLIF</b> ({source})

🚘 <b>{brand} {model}</b> ({year})
💰 Narxi: {price_display}
{profit_text}
{market_context}
📍 Manzil: <b>{location}</b>
📟 Probeg: <b>{mileage} km</b>
⚙️ Karobka: <b>{transmission}</b>
⛽ Yoqilg'i: <b>{fuel_type}</b>

{urgency_tag}
{condition_tag}
{owner_tag}
{credit_tag}

🔗 <a href="{url}">E'lonni batafsil ko'rish</a>

#avtosavdo #{source.lower()} #automarket #flipper
"""
        channel_id = settings.scraped_deals_channel_id or settings.telegram_channel_id
        
        await bot.send_message(
            chat_id=channel_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
    except Exception as e:
        logger.error(f"Error publishing scraped deal: {e}")

async def publish_admin_car(car_data: Dict):
    """
    Publish admin-added car to admin channel
    """
    try:
        text = f"""
⭐ <b>YANGI AVTOMOBIL — AVTO SAVDO</b>

🚘 Model: <b>{car_data['brand']} {car_data['model']}</b>
📅 Yili: <b>{car_data['year']}</b>
💰 Narxi: <b>{car_data['price']:,.0f} $</b>
🎨 Rangi: <b>{car_data.get('color', 'N/A')}</b>
⚙️ Uzatmalar qutisi: <b>{car_data.get('transmission', 'N/A')}</b>

📝 Ma'lumot: <i>{car_data.get('description', 'N/A')}</i>

📞 Bog'lanish: @avtosavdo_admin
🏢 #avtosavdo #premium #adminpost
"""
        channel_id = settings.admin_cars_channel_id or settings.telegram_channel_id
        
        if car_data.get('images'):
            main_photo = car_data['images'].get('main')
            gallery = car_data['images'].get('gallery', [])
            
            if main_photo:
                if gallery:
                    from aiogram.types import InputMediaPhoto
                    media = [InputMediaPhoto(media=main_photo, caption=text, parse_mode="HTML")]
                    for ph in gallery[:9]: # Max 10 items total
                        media.append(InputMediaPhoto(media=ph))
                    await bot.send_media_group(chat_id=channel_id, media=media)
                else:
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=main_photo,
                        caption=text,
                        parse_mode="HTML"
                    )
                return

        await bot.send_message(
            chat_id=channel_id,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error publishing admin car: {e}")

async def notify_admin_about_error(error_message: str):
    """
    Notify admins about critical system errors
    
    Args:
        error_message: Error message to send
    """
    global bot
    if not bot:
        return
        
    try:
        text = f"❌ **KRITIK XATOLIK!**\n\n`{error_message}`\n\nIltimos, loglarni tekshiring!"
        
        for admin_id in settings.admin_list:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error sending error to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in notify_admin_about_error: {e}")
