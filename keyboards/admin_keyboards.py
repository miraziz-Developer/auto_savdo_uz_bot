"""
Admin keyboards — Admin panel tugmalari
Pipeline, CRM, Hot Leads, e'lon boshqarish
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Admin asosiy menyusi"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Moshina qo'shish (ADMIN)"), KeyboardButton(text="📋 Pipeline")],
            [KeyboardButton(text="📊 CRM Dashboard"), KeyboardButton(text="🔥 Hot Leads")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🖥️ Tizim Monitoringi")],
            [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="💰 Sotuvni qayd qilish")],
            [KeyboardButton(text="👤 Oddiy foydalanuvchi rejimi")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin buyruqlarini tanlang..."
    )
    return keyboard


def car_management_keyboard(car_id: int = None) -> InlineKeyboardMarkup:
    """Moshina boshqarish tugmalari"""
    buttons = [
        [
            InlineKeyboardButton(text="📸 Rasm qo'shish", callback_data=f"admin:car:photo:{car_id}"),
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin:car:edit:{car_id}")
        ],
        [
            InlineKeyboardButton(text="📢 Kanalga yuborish", callback_data=f"admin:car:publish:{car_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:car:delete:{car_id}")
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def publish_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """E'lon chop etish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga yuborish", callback_data=f"admin:publish_channel:{car_id}")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data=f"admin:car_back:{car_id}")],
    ])


def inquiry_management_keyboard(inquiry_id: int) -> InlineKeyboardMarkup:
    """Murojaat boshqarish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"inquiry:accept:{inquiry_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"inquiry:reject:{inquiry_id}")
        ],
        [
            InlineKeyboardButton(text="📞 Qo'ng'iroq", callback_data=f"inquiry:call:{inquiry_id}"),
            InlineKeyboardButton(text="🏗 Katalogga o'tkazish", callback_data=f"inquiry_complete:{inquiry_id}")
        ]
    ])


def statistics_keyboard() -> InlineKeyboardMarkup:
    """Statistika tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Umumiy", callback_data="stats:general")],
        [InlineKeyboardButton(text="📈 Sotuvlar", callback_data="stats:sales")],
        [InlineKeyboardButton(text="🔝 Top modellar", callback_data="stats:top_models")],
    ])


# --- PIPELINE KEYBOARDS ---

def pipeline_keyboard() -> InlineKeyboardMarkup:
    """Pipeline asosiy menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Barcha bosqichlar", callback_data="pipeline:overview")],
        [
            InlineKeyboardButton(text="📥 Qabul", callback_data="pipeline:stage:qabul"),
            InlineKeyboardButton(text="📸 Rasm", callback_data="pipeline:stage:rasm"),
        ],
        [
            InlineKeyboardButton(text="📢 Kanal", callback_data="pipeline:stage:kanal"),
            InlineKeyboardButton(text="👁 Ko'rishlar", callback_data="pipeline:stage:ko'rishlar"),
        ],
        [
            InlineKeyboardButton(text="📞 Telefon", callback_data="pipeline:stage:telefon"),
            InlineKeyboardButton(text="🤝 Kelishildi", callback_data="pipeline:stage:kelishildi"),
        ],
        [InlineKeyboardButton(text="✅ Sotildi", callback_data="pipeline:stage:sotildi")],
    ])


def pipeline_car_keyboard(car_id: int, current_stage: str) -> InlineKeyboardMarkup:
    """Pipeline'da moshinani boshqarish"""
    stages = ["qabul", "rasm", "kanal", "ko'rishlar", "telefon", "kelishildi", "sotildi"]
    current_idx = stages.index(current_stage) if current_stage in stages else 0
    
    buttons = []
    
    if current_idx < len(stages) - 1:
        next_stage = stages[current_idx + 1]
        buttons.append([
            InlineKeyboardButton(
                text=f"➡️ Keyingi: {next_stage.capitalize()}",
                callback_data=f"pipeline:move:{car_id}:{next_stage}"
            )
        ])
    
    if current_idx > 0:
        prev_stage = stages[current_idx - 1]
        buttons.append([
            InlineKeyboardButton(
                text=f"⬅️ Oldingisiga: {prev_stage.capitalize()}",
                callback_data=f"pipeline:move:{car_id}:{prev_stage}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- BUY REQUEST ADMIN KEYBOARDS ---

def buy_request_admin_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Admin olish arizasini boshqarish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"buyreq:accept:{request_id}"),
            InlineKeyboardButton(text="📞 Qo'ng'iroq", callback_data=f"buyreq:call:{request_id}"),
        ],
        [
            InlineKeyboardButton(text="🔍 Mos variantlar", callback_data=f"buyreq:match:{request_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"buyreq:reject:{request_id}"),
        ],
    ])


# --- CRM KEYBOARDS ---

def crm_main_keyboard() -> InlineKeyboardMarkup:
    """CRM asosiy menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="crm:stats")],
        [InlineKeyboardButton(text="🔥 Hot Leads", callback_data="crm:hot_leads")],
        [InlineKeyboardButton(text="🛒 Olish arizalari", callback_data="crm:buy_requests")],
        [InlineKeyboardButton(text="📥 Sotuv arizalari", callback_data="crm:sell_inquiries")],
        [InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="crm:all_users")],
    ])


def user_profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Foydalanuvchi profili boshqaruvi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Eslatma yozish", callback_data=f"crm:note:{user_id}"),
            InlineKeyboardButton(text="📞 Aloqa qayd etish", callback_data=f"crm:contact_log:{user_id}"),
        ],
        [
            InlineKeyboardButton(text="🔄 Status o'zgartirish", callback_data=f"crm:change_status:{user_id}"),
            InlineKeyboardButton(text="📋 Arizalari", callback_data=f"crm:user_requests:{user_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Ortga", callback_data="crm:hot_leads")],
    ])


def conversion_status_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Konversiya statusi o'zgartirish"""
    statuses = [
        ("🆕 Yangi", "yangi"),
        ("🔍 Qiziqmoqda", "qiziqmoqda"),
        ("💬 Muzokara", "muzokara"),
        ("✅ Sotib oldi", "sotib_oldi"),
        ("❌ Yo'qolgan", "yo'qolgan"),
    ]
    buttons = []
    for label, status in statuses:
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"crm:set_status:{user_id}:{status}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Ortga", callback_data=f"crm:profile:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Broadcast tasdiqlash tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast:confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast:cancel")
        ]
    ])


def buy_request_management_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Olish arizasini boshqarish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"buyreq:accept:{request_id}"),
            InlineKeyboardButton(text="📞 Qo'ng'iroq", callback_data=f"buyreq:call:{request_id}"),
        ],
        [
            InlineKeyboardButton(text="🔍 Mos variantlar", callback_data=f"buyreq:match:{request_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"buyreq:reject:{request_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ Ortga", callback_data="crm:buy_requests")
        ]
    ])
