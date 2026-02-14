"""
Notifications — Xabar yuborish tizimi
Subscriber notification, push, admin alerts, channel publishing
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
    """Global bot instance ni o'rnatish"""
    global bot
    bot = bot_instance


async def notify_subscribers_about_car(user_id: int, listing_data: Dict):
    """Obunachilarga yangi e'lon haqida xabar"""
    try:
        brand = listing_data.get('brand') or "Noma'lum"
        model = listing_data.get('model') or "Noma'lum"
        year = listing_data.get('year') or "Noma'lum"
        price = listing_data.get('price', 0)
        source = listing_data.get('source', '').upper()
        
        text = (
            f"📩 <b>YANGI E'LON TOPILDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚗 <b>{brand} {model}</b> ({year})\n"
            f"💰 Narxi: <b>{price:,.0f} $</b>\n"
            f"🌐 Manba: <b>{source}</b>\n\n"
            f"✨ <i>Bu e'lon sizning qidiruv obunangizga mos keladi!</i>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Batafsil ko'rish", url=listing_data.get('url', ''))],
            [InlineKeyboardButton(text="📞 Admin bilan bog'lanish", callback_data="need_phone")]
        ])
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Notification: user {user_id} -> {brand} {model}")
        
    except Exception as e:
        logger.error(f"Notification error (user {user_id}): {e}")


async def send_push_notification(user_id: int, cars: List):
    """Haftalik push — top moshinalar"""
    try:
        text = (
            "🚀 <b>HAFTALIK TOP TAKLIFLAR!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        for i, car in enumerate(cars, 1):
            text += (
                f"{i}. <b>{car.brand} {car.model}</b> ({car.year})\n"
                f"   💰 <b>{car.price:,.0f} $</b>\n\n"
            )
        
        text += (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📍 <i>Eng yaxshi takliflarni o'tkazib yubormang!</i>\n"
            "🔍 Batafsil ko'rish uchun /start bosing."
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Push error (user {user_id}): {e}")


async def notify_admin_about_good_deal(listing_data: Dict):
    """Adminlarga arzon variant haqida xabar"""
    try:
        text = (
            f"💰 <b>ARZON VARIANT TOPILDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚗 <b>{listing_data.get('title', '')}</b>\n"
            f"💵 Narxi: <b>{listing_data.get('price', 0):,.0f} $</b>\n"
            f"🌐 Manba: <b>{listing_data.get('source', '').upper()}</b>\n\n"
            f"🔥 <i>Bu narx bozor qiymatidan sezilarli past!</i>"
        )
        
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
                logger.error(f"Admin notify error ({admin_id}): {e}")
        
    except Exception as e:
        logger.error(f"Good deal notify error: {e}")


async def publish_scraped_deal(listing_data: Dict):
    """Topilgan e'lonni kanalga chop etish"""
    try:
        source = listing_data.get('source', '').upper()
        url = listing_data.get('url', '#')
        
        brand = listing_data.get('brand') or "Noma'lum"
        model = listing_data.get('model') or "Noma'lum"
        year = listing_data.get('year') or "Noma'lum"
        price = listing_data.get('price', 0)
        location = listing_data.get('location', "Toshkent")
        mileage = listing_data.get('mileage', 0)
        transmission = listing_data.get('transmission', "noma'lum")
        fuel_type = listing_data.get('fuel_type', "noma'lum")
        description = (listing_data.get('description') or "").lower()
        
        # Tag analysis
        tags = []
        if any(w in description for w in ['srochno', 'zarur', 'tez sotiladi', 'pul kerak']):
            tags.append("🔥 <b>SHOSHILINCH!</b>")
        if any(w in description for w in ['naqd', 'faqat naqd']):
            tags.append("💵 <b>NAQD</b>")
        if any(w in description for w in ['toza', "kraska yo'q", "petno yo'q", 'radnoy']):
            tags.append("✨ <b>TOZA HOLAT</b>")
        elif 'kraska bor' in description or 'dtp' in description or 'petno' in description:
            tags.append("⚠️ <b>Kraska/DTP</b>")
        if any(w in description for w in ['ozimniki', "o'zimniki", 'tirikchilik emas', 'salondan']):
            tags.append("👨‍💼 <b>EGASIDAN</b>")
        if any(w in description for w in ['variant', 'ijara', 'boshiga', 'oyiga', 'vikup']):
            tags.append("💳 <b>VARIANT/KREDIT</b>")
        
        tags_text = "  ".join(tags) if tags else ""
        
        # Price analysis
        avg_price = listing_data.get('avg_price', 0)
        is_good_deal = listing_data.get('is_good_deal', False)
        is_price_drop = listing_data.get('is_price_drop', False)
        
        deal_tag = ""
        profit_text = ""
        
        if is_price_drop:
            old_price = listing_data.get('old_price', 0)
            diff = listing_data.get('price_diff', 0)
            deal_tag = f"📉 <b>NARX TUSHDI! (-{diff:,.0f} $)</b>\n"
            price_display = f"<s>{old_price:,.0f} $</s> ➡️ <b>{price:,.0f} $</b>"
        else:
            price_display = f"<b>{price:,.0f} $</b>"
        
        if is_good_deal and avg_price:
            diff = avg_price - price
            percent = (diff / avg_price) * 100 if avg_price else 0
            if not deal_tag:
                deal_tag = f"🤑 <b>SUPER DEAL! (BOZORDAN {percent:.0f}% ARZON)</b>\n"
            profit_text = (
                f"\n📊 O'rtacha narx: ~{avg_price:,.0f} $\n"
                f"💰 Taxminiy foyda: ~{diff:,.0f} $"
            )
        
        # Market context
        competitors = listing_data.get('competitor_count', 0)
        comp_text = f"{competitors} ta"
        if competitors < 3:
            comp_text += " (kam qolgan!)"
        elif competitors > 20:
            comp_text += " (ko'p)"
        
        liquidity = "noma'lum"
        model_lower = model.lower()
        if model_lower in LIQUIDITY_MAP:
            liquidity = LIQUIDITY_MAP[model_lower]
        else:
            for k, v in LIQUIDITY_MAP.items():
                if k in model_lower or k in brand.lower():
                    liquidity = v
                    break
        
        # Deal score
        score = listing_data.get('deal_score', 50)
        if score >= 90:
            score_bar = "🔥🔥🔥🔥🔥"
        elif score >= 70:
            score_bar = "🔥🔥🔥🔥"
        elif score >= 50:
            score_bar = "⭐⭐⭐"
        else:
            score_bar = "⭐⭐"
        
        cross_platform = ""
        if listing_data.get('cross_platform_url'):
            other = listing_data.get('cross_platform_source', 'Boshqa').upper()
            cross_platform = f"\n⚠️ <b>BU MOSHINA {other} DA HAM BOR!</b>\n"
        
        text = (
            f"{deal_tag}"
            f"🚗 <b>YANGI TAKLIF</b> ({source})\n"
            f"{score_bar} Deal balli: <b>{score}/100</b>\n"
            f"{cross_platform}\n"
            f"🚘 <b>{brand} {model}</b> ({year})\n"
            f"💰 Narxi: {price_display}\n"
            f"{profit_text}\n\n"
            f"📊 <b>BOZOR TAHLILI:</b>\n"
            f"📉 Raqobatchilar: <b>{comp_text}</b>\n"
            f"⏳ Sotilish tezligi: <b>{liquidity}</b>\n\n"
            f"📍 Joylashuv: <b>{location}</b>\n"
            f"🛣 Probeg: <b>{mileage} km</b>\n"
            f"⚙️ Karobka: <b>{transmission}</b>\n"
            f"⛽ Yoqilg'i: <b>{fuel_type}</b>\n\n"
            f"{tags_text}\n\n"
            f"🔗 <a href=\"{url}\">E'lonni batafsil ko'rish</a>\n\n"
            f"#avtosavdo #{source.lower()} #automarket"
        )
        
        channel_id = settings.scraped_deals_channel_id or settings.telegram_channel_id
        
        await bot.send_message(
            chat_id=channel_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
    except Exception as e:
        logger.error(f"Publish scraped deal error: {e}")


async def publish_admin_car(car_data: Dict):
    """Admin qo'shgan moshinani kanalga chop etish"""
    try:
        text = (
            "⭐ <b>YANGI AVTOMOBIL — AVTO SAVDO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚘 <b>{car_data['brand']} {car_data['model']}</b>\n"
            f"📅 Yili: <b>{car_data['year']}</b>\n"
            f"💰 Narxi: <b>{car_data['price']:,.0f} $</b>\n"
            f"🎨 Rangi: <b>{car_data.get('color', 'N/A')}</b>\n"
            f"⚙️ Uzatma: <b>{car_data.get('transmission', 'N/A')}</b>\n\n"
            f"📝 <i>{car_data.get('description', '')}</i>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📞 Bog'lanish: @avtosavdo_admin\n"
            "🏢 #avtosavdo #premium"
        )
        
        channel_id = settings.admin_cars_channel_id or settings.telegram_channel_id
        
        if car_data.get('images'):
            main_photo = car_data['images'].get('main')
            gallery = car_data['images'].get('gallery', [])
            
            if main_photo:
                if gallery:
                    from aiogram.types import InputMediaPhoto
                    media = [InputMediaPhoto(media=main_photo, caption=text, parse_mode="HTML")]
                    for ph in gallery[:9]:
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
        logger.error(f"Publish admin car error: {e}")


async def notify_admin_about_error(error_message: str):
    """Adminlarga kritik xatolik haqida xabar"""
    global bot
    if not bot:
        return
    
    try:
        text = (
            "🚨 <b>KRITIK XATOLIK!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{error_message}</code>\n\n"
            "⚠️ <i>Iltimos, loglarni tekshiring!</i>"
        )
        
        for admin_id in settings.admin_list:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error notify admin {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"notify_admin_about_error: {e}")
