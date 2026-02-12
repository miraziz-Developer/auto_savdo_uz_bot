"""
Admin keyboards for the bot
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def admin_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard for admins"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="➕ Moshina qo'shish (ADMIN)"),
        KeyboardButton(text="📋 Admin: Moshinalar")
    )
    builder.row(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="💰 Sotuvni qayd qilish")
    )
    builder.row(
        KeyboardButton(text="📥 Murojaatlar"),
        KeyboardButton(text="📊 CRM Dashboard")
    )
    builder.row(
        KeyboardButton(text="🔍 Parsing Dashboard"),
        KeyboardButton(text="📢 Xabar yuborish")
    )
    builder.row(
        KeyboardButton(text="👤 Oddiy foydalanuvchi rejimi")
    )
    return builder.as_markup(resize_keyboard=True)


def car_management_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Car management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin:car:edit:{car_id}"),
        InlineKeyboardButton(text="❌ O'chirish", callback_data=f"admin:car:delete:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin:car:stats:{car_id}"),
        InlineKeyboardButton(text="⭐ Featured", callback_data=f"admin:car:feature:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📤 E'lon qilish", callback_data=f"admin:car:publish:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:cars:list")
    )
    return builder.as_markup()


def publish_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Publishing options keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📱 Telegram", callback_data=f"publish:telegram:{car_id}"),
        InlineKeyboardButton(text="📸 Instagram", callback_data=f"publish:instagram:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Hammasi", callback_data=f"publish:all:{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"admin:car:view:{car_id}")
    )
    return builder.as_markup()


def inquiry_management_keyboard(inquiry_id: int) -> InlineKeyboardMarkup:
    """Inquiry management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Qabul", callback_data=f"inquiry:accept:{inquiry_id}"),
        InlineKeyboardButton(text="❌ Rad", callback_data=f"inquiry:reject:{inquiry_id}"),
        InlineKeyboardButton(text="🏆 Bajarish", callback_data=f"inquiry_complete:{inquiry_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📞 Qo'ng'iroq", callback_data=f"inquiry:call:{inquiry_id}"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:inquiries:list")
    )
    return builder.as_markup()


def scraped_listing_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    """Scraped listing action keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Qo'shish", callback_data=f"scraped:add:{listing_id}"),
        InlineKeyboardButton(text="📤 Dadaga yuborish", callback_data=f"scraped:send:{listing_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Inkor", callback_data=f"scraped:skip:{listing_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Linkni ochish", url=f"placeholder_{listing_id}")
    )
    return builder.as_markup()


def statistics_keyboard() -> InlineKeyboardMarkup:
    """Statistics options keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Sotuvlar", callback_data="stats:sales"),
        InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="stats:users")
    )
    builder.row(
        InlineKeyboardButton(text="🚗 Moshinalar", callback_data="stats:cars"),
        InlineKeyboardButton(text="💰 Foyda", callback_data="stats:profit")
    )
    builder.row(
        InlineKeyboardButton(text="📊 To'liq hisobot", callback_data="stats:full")
    )
    return builder.as_markup()


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Broadcast confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast:confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast:cancel")
    )
    return builder.as_markup()
