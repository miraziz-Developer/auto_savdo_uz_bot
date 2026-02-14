"""
Pipeline Handler — Moshina Sotish Jarayonini Kuzatish (Admin)
Kanban-style pipeline: Qabul → Rasm → Kanal → Ko'rishlar → Telefon → Kelishildi → Sotildi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import settings
from database.database import async_session_maker
from database.crud import (
    get_cars_by_pipeline, update_car_pipeline, get_car_by_id,
    is_admin
)
from keyboards.admin_keyboards import admin_main_menu_keyboard

router = Router()

PIPELINE_STAGES = {
    "qabul": {"emoji": "📥", "name": "Qabul qilindi", "order": 1},
    "rasm_olindi": {"emoji": "📸", "name": "Rasm olindi", "order": 2},
    "kanalga_joylandi": {"emoji": "📢", "name": "Kanalga joylandi", "order": 3},
    "korishlar": {"emoji": "👀", "name": "Ko'rishlar/qiziqish", "order": 4},
    "telefon": {"emoji": "📞", "name": "Telefon qilindi", "order": 5},
    "kelishildi": {"emoji": "🤝", "name": "Kelishildi", "order": 6},
    "sotildi": {"emoji": "💰", "name": "Sotildi!", "order": 7},
}

PIPELINE_ORDER = ["qabul", "rasm_olindi", "kanalga_joylandi", "korishlar", "telefon", "kelishildi", "sotildi"]


@router.message(F.text == "📋 Pipeline")
async def show_pipeline(message: Message):
    """Show pipeline overview"""
    if message.from_user.id not in settings.admin_list:
        return
    
    async with async_session_maker() as session:
        all_cars = await get_cars_by_pipeline(session)
    
    if not all_cars:
        await message.answer(
            "📋 <b>PIPELINE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Hozircha pipeline bo'sh.\n"
            "Moshinalarni ➕ Moshina qo'shish orqali qo'shing!",
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Group by stage
    stages = {s: [] for s in PIPELINE_ORDER}
    for car in all_cars:
        status = car.pipeline_status or "qabul"
        if status in stages:
            stages[status].append(car)
        else:
            stages["qabul"].append(car)
    
    text = "📋 <b>PIPELINE — Sotish Jarayoni</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    total = len(all_cars)
    
    for stage_key in PIPELINE_ORDER:
        stage = PIPELINE_STAGES[stage_key]
        cars_in_stage = stages[stage_key]
        count = len(cars_in_stage)
        
        bar_filled = "█" * min(count, 10)
        bar_empty = "░" * (10 - min(count, 10))
        
        text += f"{stage['emoji']} <b>{stage['name']}</b> — {count} ta\n"
        text += f"    {bar_filled}{bar_empty}\n"
        
        for car in cars_in_stage[:3]:
            text += f"    • {car.brand} {car.model} ({car.year}) — {car.price:,.0f}$\n"
        
        if count > 3:
            text += f"    <i>... va yana {count - 3} ta</i>\n"
        
        text += "\n"
    
    text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 Jami: <b>{total}</b> ta moshina\n"
    
    # Stage filter buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Qabul", callback_data="pipeline:view:qabul"),
            InlineKeyboardButton(text="📸 Rasm", callback_data="pipeline:view:rasm_olindi"),
            InlineKeyboardButton(text="📢 Kanal", callback_data="pipeline:view:kanalga_joylandi"),
        ],
        [
            InlineKeyboardButton(text="👀 Ko'rishlar", callback_data="pipeline:view:korishlar"),
            InlineKeyboardButton(text="📞 Telefon", callback_data="pipeline:view:telefon"),
            InlineKeyboardButton(text="🤝 Kelishildi", callback_data="pipeline:view:kelishildi"),
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="pipeline:refresh"),
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "pipeline:refresh")
async def refresh_pipeline(callback: CallbackQuery):
    """Refresh pipeline data"""
    async with async_session_maker() as session:
        all_cars = await get_cars_by_pipeline(session)
    
    stages = {s: [] for s in PIPELINE_ORDER}
    for car in all_cars:
        status = car.pipeline_status or "qabul"
        if status in stages:
            stages[status].append(car)
    
    text = "📋 <b>PIPELINE — Yangilandi ✅</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for stage_key in PIPELINE_ORDER:
        stage = PIPELINE_STAGES[stage_key]
        count = len(stages[stage_key])
        text += f"{stage['emoji']} {stage['name']}: <b>{count}</b> ta\n"
    
    text += f"\n📊 Jami: <b>{len(all_cars)}</b> ta"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Qabul", callback_data="pipeline:view:qabul"),
            InlineKeyboardButton(text="📸 Rasm", callback_data="pipeline:view:rasm_olindi"),
            InlineKeyboardButton(text="📢 Kanal", callback_data="pipeline:view:kanalga_joylandi"),
        ],
        [
            InlineKeyboardButton(text="👀 Ko'rishlar", callback_data="pipeline:view:korishlar"),
            InlineKeyboardButton(text="📞 Telefon", callback_data="pipeline:view:telefon"),
            InlineKeyboardButton(text="🤝 Kelishildi", callback_data="pipeline:view:kelishildi"),
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="pipeline:refresh"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Yangilandi")


@router.callback_query(F.data.startswith("pipeline:view:"))
async def view_pipeline_stage(callback: CallbackQuery):
    """View cars in a specific pipeline stage"""
    stage_key = callback.data.split(":")[2]
    stage = PIPELINE_STAGES.get(stage_key)
    
    if not stage:
        await callback.answer("❌ Noto'g'ri bosqich", show_alert=True)
        return
    
    async with async_session_maker() as session:
        cars = await get_cars_by_pipeline(session, stage_key)
    
    if not cars:
        await callback.answer(f"{stage['emoji']} Bu bosqichda moshina yo'q", show_alert=True)
        return
    
    text = f"{stage['emoji']} <b>{stage['name']}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    buttons = []
    for car in cars[:10]:
        text += (
            f"🚗 <b>{car.brand} {car.model}</b> ({car.year})\n"
            f"   💰 {car.price:,.0f} $ | 👁 {car.views_count} ko'rish\n"
        )
        if car.pipeline_updated_at:
            text += f"   ⏰ {car.pipeline_updated_at.strftime('%d.%m %H:%M')}\n"
        text += "\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"🔄 {car.brand} {car.model} ({car.id})",
                callback_data=f"pipeline:car:{car.id}"
            )
        ])
    
    if len(cars) > 10:
        text += f"<i>... va yana {len(cars) - 10} ta</i>"
    
    buttons.append([InlineKeyboardButton(text="◀️ Pipeline", callback_data="pipeline:refresh")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pipeline:car:"))
async def manage_car_pipeline(callback: CallbackQuery):
    """Show pipeline options for specific car"""
    car_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
    
    if not car:
        await callback.answer("❌ Moshina topilmadi", show_alert=True)
        return
    
    current_stage = car.pipeline_status or "qabul"
    current_info = PIPELINE_STAGES.get(current_stage, PIPELINE_STAGES["qabul"])
    
    text = (
        f"🚗 <b>{car.brand} {car.model} ({car.year})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Narx: <b>{car.price:,.0f} $</b>\n"
        f"👁 Ko'rishlar: {car.views_count}\n\n"
        f"📋 Hozirgi: {current_info['emoji']} <b>{current_info['name']}</b>\n\n"
        f"🔄 Bosqichni o'zgartiring:"
    )
    
    buttons = []
    for stage_key in PIPELINE_ORDER:
        stage = PIPELINE_STAGES[stage_key]
        prefix = "✅ " if stage_key == current_stage else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix}{stage['emoji']} {stage['name']}",
                callback_data=f"pipeline:set:{car_id}:{stage_key}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="pipeline:refresh")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pipeline:set:"))
async def set_car_pipeline(callback: CallbackQuery):
    """Update car pipeline stage"""
    parts = callback.data.split(":")
    car_id = int(parts[2])
    new_stage = parts[3]
    
    stage = PIPELINE_STAGES.get(new_stage)
    if not stage:
        await callback.answer("❌ Noto'g'ri bosqich", show_alert=True)
        return
    
    async with async_session_maker() as session:
        await update_car_pipeline(session, car_id, new_stage)
        car = await get_car_by_id(session, car_id)
        
        # If sold, mark as unavailable
        if new_stage == "sotildi" and car:
            from database.crud import update_car
            await update_car(session, car_id, is_available=False)
    
    await callback.answer(
        f"✅ {car.brand} {car.model} → {stage['emoji']} {stage['name']}",
        show_alert=True
    )
    
    # Refresh the car view
    await manage_car_pipeline(callback)
