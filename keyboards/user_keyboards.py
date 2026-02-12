"""
User keyboards for the bot
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard for users"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🚗 Katalog"),
        KeyboardButton(text="🔍 Qidiruv")
    )
    builder.row(
        KeyboardButton(text="🔔 Obuna"),
        KeyboardButton(text="❤️ Sevimlilar")
    )
    builder.row(
        KeyboardButton(text="🚗 Mashina sotish"),
        KeyboardButton(text="📝 Mening e'lonlarim")
    )
    builder.row(
        KeyboardButton(text="🔔 Obuna"),
        KeyboardButton(text="📊 Mening obunalarim")
    )
    builder.row(
        KeyboardButton(text="❤️ Sevimlilar"),
        KeyboardButton(text="ℹ️ Yordam")
    )
    return builder.as_markup(resize_keyboard=True)


def request_phone_keyboard() -> ReplyKeyboardMarkup:
    """Request phone number keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True))
    builder.row(KeyboardButton(text="◀️ Orqaga"))
    return builder.as_markup(resize_keyboard=True)


def car_filters_keyboard(data: dict = None) -> InlineKeyboardMarkup:
    """Car filters inline keyboard with active indicators"""
    data = data or {}
    builder = InlineKeyboardBuilder()
    
    brand_text = f"🏷 Brend {'✅' if data.get('filter_brand') else ''}"
    model_text = f"🚙 Model {'✅' if data.get('filter_model') else ''}"
    year_text = f"📅 Yil {'✅' if data.get('filter_year') else ''}"
    price_text = f"💵 Narx {'✅' if data.get('filter_price') else ''}"
    
    builder.row(
        InlineKeyboardButton(text=brand_text, callback_data="filter:brand"),
        InlineKeyboardButton(text=model_text, callback_data="filter:model")
    )
    builder.row(
        InlineKeyboardButton(text=year_text, callback_data="filter:year"),
        InlineKeyboardButton(text=price_text, callback_data="filter:price")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Tozalash", callback_data="filter:reset")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Qidirish", callback_data="filter:search")
    )
    return builder.as_markup()


def car_detail_keyboard(car_id: int, has_phone: bool = False) -> InlineKeyboardMarkup:
    """Car detail inline keyboard"""
    builder = InlineKeyboardBuilder()
    
    if has_phone:
        builder.row(
            InlineKeyboardButton(text="📞 Bog'lanish", callback_data=f"car:contact:{car_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="📞 Bog'lanish (telefon kerak)", callback_data="need_phone")
        )
    
    builder.row(
        InlineKeyboardButton(text="❤️ Sevimlilar", callback_data=f"car:favorite:{car_id}"),
        InlineKeyboardButton(text="⭐ Sharh yozish", callback_data=f"car:review:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Sharhlar", callback_data=f"car:reviews:{car_id}"),
        InlineKeyboardButton(text="🖼 Rasmlar", callback_data=f"car:gallery:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📤 Ulashish", callback_data=f"car:share:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back:catalog")
    )
    
    return builder.as_markup()


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Subscription management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Yangi obuna", callback_data="subscription:new")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Mening obunalarim", callback_data="subscription:list")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")
    )
    return builder.as_markup()


def subscription_item_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """Individual subscription keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ O'chirish", callback_data=f"subscription:delete:{subscription_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="subscription:list")
    )
    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm:{action}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=f"cancel:{action}")
    )
    return builder.as_markup()


def pagination_keyboard(page: int, total_pages: int, prefix: str = "page") -> InlineKeyboardMarkup:
    """Pagination keyboard"""
    builder = InlineKeyboardBuilder()
    
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{page-1}"))
    
    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="page:current"))
    
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{page+1}"))
    
    builder.row(*buttons)
    return builder.as_markup()


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)
