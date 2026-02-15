"""
User keyboards — Foydalanuvchi uchun klaviaturalar
Asosiy, filtr, katalog, obuna va boshqa tugmalar
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu — foydalanuvchi uchun"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Moshina olish"), KeyboardButton(text="➕ E'lon berish")],
            [KeyboardButton(text="🔍 Qidiruv"), KeyboardButton(text="🚗 Katalog")],
            [KeyboardButton(text="📊 Narxni baholash"), KeyboardButton(text="📉 Arzon variantlar")],
            [KeyboardButton(text="🔔 Obunalar"), KeyboardButton(text="❤️ Sevimlilar")],
            [KeyboardButton(text="📋 Mening arizalarim")],
            [KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Quyidagi tugmalardan tanlang..."
    )
    return keyboard


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def confirm_keyboard(action: str = "") -> InlineKeyboardMarkup:
    """Tasdiqlash tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm:{action}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel:{action}")
        ]
    ])


def request_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqam so'rash"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def car_filters_keyboard(current_filters: dict = None) -> InlineKeyboardMarkup:
    """Qidiruv filtrlari — tanlangan filtrlarni ko'rsatadi"""
    if not current_filters:
        current_filters = {}
    
    brand_label = f"🏷 Brend: {current_filters['filter_brand']}" if current_filters.get('filter_brand') else "🏷 Brend"
    model_label = f"🚙 Model: {current_filters['filter_model']}" if current_filters.get('filter_model') else "🚙 Model"
    year_label = f"📅 Yil: {current_filters['filter_year']}+" if current_filters.get('filter_year') else "📅 Yil"
    price_label = f"💰 Narx: {current_filters['filter_price']:,.0f}$" if current_filters.get('filter_price') else "💰 Narx"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=brand_label, callback_data="filter:brand"),
            InlineKeyboardButton(text=model_label, callback_data="filter:model"),
        ],
        [
            InlineKeyboardButton(text=year_label, callback_data="filter:year"),
            InlineKeyboardButton(text=price_label, callback_data="filter:price"),
        ],
        [
            InlineKeyboardButton(text="✅ Qidirish", callback_data="filter:search"),
        ],
        [
            InlineKeyboardButton(text="♻️ Tozalash", callback_data="filter:reset"),
        ]
    ])
    return keyboard


def car_detail_keyboard(car_id: int, has_phone: bool = False) -> InlineKeyboardMarkup:
    """Moshina tafsilotlari tugmalari"""
    keyboard = [
        [
            InlineKeyboardButton(text="📞 Bog'lanish", callback_data=f"car:contact:{car_id}"),
            InlineKeyboardButton(text="❤️", callback_data=f"car:favorite:{car_id}"),
        ],
        [
            InlineKeyboardButton(text="📸 Rasmlar", callback_data=f"car:gallery:{car_id}"),
            InlineKeyboardButton(text="⭐ Sharhlar", callback_data=f"car:reviews:{car_id}"),
        ],
        [
            InlineKeyboardButton(text="✍️ Sharh yozish", callback_data=f"car:review:{car_id}"),
            InlineKeyboardButton(text="📤 Ulashish", callback_data=f"car:share:{car_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def pagination_keyboard(current_page: int, total_pages: int, prefix: str = "page") -> InlineKeyboardMarkup:
    """Sahifalash tugmalari"""
    buttons = []
    
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:{current_page - 1}"))
    
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:{current_page + 1}"))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Obunalar menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi obuna yaratish", callback_data="subscription:new")],
        [InlineKeyboardButton(text="📋 Mening obunalarim", callback_data="subscription:list")],
    ])


def subscription_item_keyboard(sub_id: int) -> InlineKeyboardMarkup:
    """Obunani boshqarish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"subscription:delete:{sub_id}")],
    ])


def scraped_listing_keyboard(url: str, source: str) -> InlineKeyboardMarkup:
    """Topilgan e'lon tugmalari"""
    buttons = [
        [InlineKeyboardButton(text=f"🔗 {source.upper()} da ko'rish", url=url)],
        [InlineKeyboardButton(text="📞 Admin bilan bog'lanish", callback_data="need_phone")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def buy_request_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Olish arizasi tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Batafsil", callback_data=f"buyreq:detail:{request_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"buyreq:cancel:{request_id}")
        ]
    ])
