"""
CRM Dashboard — Enhanced with Hot Leads, User Profiles, Contact Logging
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from loguru import logger

from config import settings
from database.database import async_session_maker
from database.models import User, Inquiry, Car, Subscription, BuyRequest
from database.crud import (
    get_admin_dashboard_stats, get_hot_leads, get_user_by_id,
    get_contact_history, create_contact_log, update_user_conversion,
    get_user_inquiries, get_user_buy_requests, get_pending_buy_requests
)
from sqlalchemy import select, func, and_
from keyboards.admin_keyboards import admin_main_menu_keyboard, user_profile_keyboard, buy_request_management_keyboard
from states.states import ContactLogStates, AdminNoteStates
from utils.lead_scoring import get_lead_score_emoji, get_urgency_emoji, get_urgency_text

router = Router()


@router.message(F.text == "📊 CRM Dashboard")
async def show_crm_dashboard(message: Message):
    """Show enhanced CRM dashboard"""
    if message.from_user.id not in settings.admin_list:
        return
    
    async with async_session_maker() as session:
        stats = await get_admin_dashboard_stats(session)
    
    text = "📊 <b>CRM DASHBOARD</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Users
    text += "👥 <b>FOYDALANUVCHILAR</b>\n"
    text += f"   📊 Jami: <b>{stats['total_users']}</b>\n"
    text += f"   🟢 Faol (7 kun): <b>{stats['active_users_7d']}</b>\n"
    text += f"   🆕 Yangi (30 kun): <b>{stats['new_users_30d']}</b>\n"
    text += f"   🔥 Hot leads: <b>{stats['hot_leads']}</b>\n\n"
    
    # Cars
    text += "🚗 <b>MOSHINALAR</b>\n"
    text += f"   📦 Aktiv e'lonlar: <b>{stats['total_cars']}</b>\n\n"
    
    # Requests
    text += "📥 <b>MUROJAATLAR</b>\n"
    text += f"   ⏳ Kutayotgan: <b>{stats['pending_inquiries']}</b>\n"
    text += f"   📊 Oylik: <b>{stats['total_inquiries_30d']}</b>\n\n"
    
    # Buy Requests
    text += "🛒 <b>SOTIB OLISH ARIZALARI</b>\n"
    text += f"   ⏳ Kutayotgan: <b>{stats['pending_buy_requests']}</b>\n\n"
    
    # Sales
    text += "💰 <b>SOTUVLAR (30 kun)</b>\n"
    text += f"   🏆 Sotilgan: <b>{stats['sold_30d']} ta</b>\n"
    text += f"   💵 Foyda: <b>{stats['profit_30d']:,.0f} $</b>\n"
    
    text += f"\n⏰ <i>{datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Hot Leads", callback_data="crm:hot_leads"),
            InlineKeyboardButton(text="🛒 Olish arizalari", callback_data="crm:buy_requests")
        ],
        [
            InlineKeyboardButton(text="📥 Murojaatlar", callback_data="crm:inquiries"),
            InlineKeyboardButton(text="👥 Barcha mijozlar", callback_data="crm:all_users")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="crm:refresh")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "crm:refresh")
async def refresh_crm(callback: CallbackQuery):
    """Refresh CRM dashboard"""
    async with async_session_maker() as session:
        stats = await get_admin_dashboard_stats(session)
    
    text = "📊 <b>CRM — Yangilandi ✅</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b> | Faol: {stats['active_users_7d']}\n"
    text += f"🔥 Hot leads: <b>{stats['hot_leads']}</b>\n"
    text += f"📥 Kutayotgan murojaatlar: <b>{stats['pending_inquiries']}</b>\n"
    text += f"🛒 Olish arizalari: <b>{stats['pending_buy_requests']}</b>\n"
    text += f"💰 Oylik foyda: <b>{stats['profit_30d']:,.0f} $</b>\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Hot Leads", callback_data="crm:hot_leads"),
            InlineKeyboardButton(text="🛒 Olish arizalari", callback_data="crm:buy_requests")
        ],
        [
            InlineKeyboardButton(text="📥 Murojaatlar", callback_data="crm:inquiries"),
            InlineKeyboardButton(text="👥 Barcha mijozlar", callback_data="crm:all_users")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="crm:refresh")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Yangilandi")


# ====== HOT LEADS ======

@router.message(F.text == "🔥 Hot Leads")
async def show_hot_leads_message(message: Message):
    """Show hot leads from message"""
    if message.from_user.id not in settings.admin_list:
        return
    await _show_hot_leads(message)


@router.callback_query(F.data == "crm:hot_leads")
async def show_hot_leads_callback(callback: CallbackQuery):
    """Show hot leads from callback"""
    await _show_hot_leads(callback)
    

async def _show_hot_leads(event):
    """Show hot leads — yuqori ball olgan mijozlar"""
    async with async_session_maker() as session:
        leads = await get_hot_leads(session, min_score=40, limit=20)
    
    if not leads:
        text = (
            "🔥 <b>HOT LEADS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Hozircha yuqori balli mijozlar yo'q."
        )
    else:
        text = "🔥 <b>HOT LEADS — Jiddiy mijozlar</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, user in enumerate(leads, 1):
            name = user.full_name or user.username or f"ID: {user.telegram_id}"
            score_emoji = get_lead_score_emoji(user.lead_score)
            
            text += f"{i}. {score_emoji} <b>{name}</b>\n"
            text += f"   📊 Ball: <b>{user.lead_score}/100</b>"
            
            if user.phone:
                text += f" | 📞 {user.phone}"
            
            text += f"\n   🔄 Status: {user.conversion_status}\n"
            
            if user.preferred_brands:
                text += f"   🏷 Brendlar: {user.preferred_brands}\n"
            
            if user.budget_min and user.budget_max:
                text += f"   💰 Budjet: {user.budget_min:,.0f}-{user.budget_max:,.0f} $\n"
            
            if user.last_contacted_at:
                days_ago = (datetime.utcnow() - user.last_contacted_at).days
                text += f"   ⏰ Oxirgi aloqa: {days_ago} kun oldin\n"
            else:
                text += f"   ⏰ <i>Hali bog'lanilmagan!</i>\n"
            
            text += "\n"
    
    buttons = []
    for user in leads[:5]:
        name = user.full_name or user.username or str(user.telegram_id)
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {name} ({user.lead_score} ball)",
                callback_data=f"crm:user:{user.telegram_id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Dashboard", callback_data="crm:refresh")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ====== USER PROFILE ======

@router.callback_query(F.data.startswith("crm:user:"))
async def show_user_profile(callback: CallbackQuery):
    """Show detailed user profile"""
    user_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
            return
        
        contact_history = await get_contact_history(session, user_id, limit=5)
        user_inquiries = await get_user_inquiries(session, user_id)
        user_buy_requests = await get_user_buy_requests(session, user_id)
    
    name = user.full_name or user.username or f"ID: {user.telegram_id}"
    score_emoji = get_lead_score_emoji(user.lead_score)
    
    text = f"👤 <b>MIJOZ PROFILI</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📛 Ismi: <b>{name}</b>\n"
    if user.username:
        text += f"📱 Username: @{user.username}\n"
    text += f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
    if user.phone:
        text += f"📞 Telefon: <b>{user.phone}</b>\n"
    
    text += f"\n{score_emoji} <b>Lead Score: {user.lead_score}/100</b>\n"
    text += f"🔄 Status: <b>{user.conversion_status}</b>\n"
    text += f"👁 Ko'rishlar: {user.total_views}\n"
    text += f"📥 Murojaatlar: {user.total_inquiries}\n"
    
    if user.preferred_brands:
        text += f"🏷 Brendlar: {user.preferred_brands}\n"
    if user.budget_min and user.budget_max:
        text += f"💰 Budjet: {user.budget_min:,.0f}-{user.budget_max:,.0f} $\n"
    
    text += f"\n📅 Ro'yxatdan o'tgan: {user.created_at.strftime('%d.%m.%Y')}\n"
    if user.last_contacted_at:
        text += f"📞 Oxirgi aloqa: {user.last_contacted_at.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"⏰ So'nggi faollik: {user.last_activity.strftime('%d.%m.%Y %H:%M')}\n"
    
    if user.admin_notes:
        text += f"\n📝 <b>Admin eslatmalari:</b>\n{user.admin_notes}\n"
    
    # Contact history
    if contact_history:
        text += f"\n📜 <b>Aloqa tarixi:</b>\n"
        for log in contact_history[:3]:
            text += f"  • {log.contact_type} — {log.created_at.strftime('%d.%m %H:%M')}"
            if log.result:
                text += f" ({log.result})"
            text += "\n"
    
    # Inquiries summary
    if user_inquiries:
        text += f"\n📥 <b>Murojaatlar: {len(user_inquiries)} ta</b>\n"
    if user_buy_requests:
        text += f"🛒 <b>Olish arizalari: {len(user_buy_requests)} ta</b>\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=user_profile_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()


# ====== CONTACT LOGGING ======

@router.callback_query(F.data.startswith("admin:contact_log:"))
async def start_contact_log(callback: CallbackQuery, state: FSMContext):
    """Start logging contact with client"""
    user_id = int(callback.data.split(":")[2])
    await state.update_data(target_user_id=user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📞 Qo'ng'iroq", callback_data="clog:type:call"),
            InlineKeyboardButton(text="💬 Xabar", callback_data="clog:type:message")
        ],
        [
            InlineKeyboardButton(text="🤝 Uchrashuv", callback_data="clog:type:meeting"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="clog:cancel")
        ]
    ])
    
    await callback.message.edit_text(
        "📞 <b>Aloqa turi:</b>\n\nQaysi turdagi aloqa bo'ldi?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(ContactLogStates.waiting_for_type)


@router.callback_query(F.data.startswith("clog:type:"), ContactLogStates.waiting_for_type)
async def process_contact_type(callback: CallbackQuery, state: FSMContext):
    """Process contact type"""
    contact_type = callback.data.split(":")[2]
    await state.update_data(contact_type=contact_type)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qiziqdi", callback_data="clog:result:interested"),
            InlineKeyboardButton(text="❌ Qiziqmadi", callback_data="clog:result:not_interested")
        ],
        [
            InlineKeyboardButton(text="🔄 Qayta aloqa", callback_data="clog:result:callback"),
            InlineKeyboardButton(text="🤝 Deal!", callback_data="clog:result:deal_made")
        ],
        [
            InlineKeyboardButton(text="📵 Javob bermadi", callback_data="clog:result:no_answer")
        ]
    ])
    
    await callback.message.edit_text(
        "📋 <b>Natija:</b>\n\nAloqa natijasi qanday bo'ldi?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(ContactLogStates.waiting_for_result)


@router.callback_query(F.data.startswith("clog:result:"), ContactLogStates.waiting_for_result)
async def process_contact_result(callback: CallbackQuery, state: FSMContext):
    """Save contact log"""
    result = callback.data.split(":")[2]
    data = await state.get_data()
    
    async with async_session_maker() as session:
        await create_contact_log(
            session,
            admin_id=callback.from_user.id,
            user_id=data['target_user_id'],
            contact_type=data['contact_type'],
            result=result
        )
        
        # Update conversion status based on result
        status_map = {
            "interested": "qiziqmoqda",
            "callback": "muzokara",
            "deal_made": "sotib_oldi",
            "not_interested": "yangi",
            "no_answer": None
        }
        new_status = status_map.get(result)
        if new_status:
            await update_user_conversion(session, data['target_user_id'], new_status)
    
    await state.clear()
    
    result_text = {
        "interested": "✅ Qiziqdi",
        "not_interested": "❌ Qiziqmadi",
        "callback": "🔄 Qayta aloqa kerak",
        "deal_made": "🤝 Deal qilindi!",
        "no_answer": "📵 Javob bermadi"
    }
    
    await callback.message.edit_text(
        f"✅ <b>Aloqa qayd qilindi!</b>\n\n"
        f"📞 Turi: {data['contact_type']}\n"
        f"📋 Natija: {result_text.get(result, result)}",
        parse_mode="HTML"
    )
    await callback.answer("✅ Saqlandi!")


@router.callback_query(F.data == "clog:cancel")
async def cancel_contact_log(callback: CallbackQuery, state: FSMContext):
    """Cancel contact logging"""
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi")
    await callback.answer()


# ====== ADMIN NOTES ======

@router.callback_query(F.data.startswith("admin:note:"))
async def start_admin_note(callback: CallbackQuery, state: FSMContext):
    """Start adding note to user"""
    user_id = int(callback.data.split(":")[2])
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        "📝 <b>Eslatma yozing:</b>\n\n"
        "Bu mijoz haqida eslatma qoldiring.\n"
        "Masalan: 'Chevrolet Gentra qidiryapti, 15,000$ budjet'\n\n"
        "/skip — bekor qilish",
        parse_mode="HTML"
    )
    await state.set_state(AdminNoteStates.waiting_for_note)
    await callback.answer()


@router.message(AdminNoteStates.waiting_for_note)
async def save_admin_note(message: Message, state: FSMContext):
    """Save admin note"""
    if message.text == "/skip":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_main_menu_keyboard())
        return
    
    data = await state.get_data()
    user_id = data['target_user_id']
    
    async with async_session_maker() as session:
        user = await get_user_by_id(session, user_id)
        if user:
            existing_notes = user.admin_notes or ""
            timestamp = datetime.utcnow().strftime('%d.%m.%Y %H:%M')
            new_note = f"[{timestamp}] {message.text}"
            user.admin_notes = f"{existing_notes}\n{new_note}" if existing_notes else new_note
            await session.commit()
    
    await state.clear()
    await message.answer(
        "✅ Eslatma saqlandi!",
        reply_markup=admin_main_menu_keyboard()
    )


# ====== USER STATUS CHANGE ======

@router.callback_query(F.data.startswith("admin:status:"))
async def show_status_options(callback: CallbackQuery):
    """Show conversion status options"""
    user_id = int(callback.data.split(":")[2])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆕 Yangi", callback_data=f"set_status:{user_id}:yangi"),
            InlineKeyboardButton(text="👀 Qiziqmoqda", callback_data=f"set_status:{user_id}:qiziqmoqda"),
        ],
        [
            InlineKeyboardButton(text="🤝 Muzokara", callback_data=f"set_status:{user_id}:muzokara"),
            InlineKeyboardButton(text="✅ Sotib oldi", callback_data=f"set_status:{user_id}:sotib_oldi"),
        ],
        [
            InlineKeyboardButton(text="↩️ Qaytdi", callback_data=f"set_status:{user_id}:qaytdi"),
            InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"crm:user:{user_id}")
        ]
    ])
    
    await callback.message.edit_text(
        "🔄 <b>Mijoz statusini tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_status:"))
async def set_user_status(callback: CallbackQuery):
    """Set user conversion status"""
    parts = callback.data.split(":")
    user_id = int(parts[1])
    status = parts[2]
    
    async with async_session_maker() as session:
        await update_user_conversion(session, user_id, status)
    
    status_text = {
        "yangi": "🆕 Yangi",
        "qiziqmoqda": "👀 Qiziqmoqda",
        "muzokara": "🤝 Muzokara",
        "sotib_oldi": "✅ Sotib oldi",
        "qaytdi": "↩️ Qaytdi"
    }
    
    await callback.answer(f"✅ Status: {status_text.get(status, status)}", show_alert=True)
    # Return to user profile
    callback.data = f"crm:user:{user_id}"
    await show_user_profile(callback)


# ====== CONTACT HISTORY ======

@router.callback_query(F.data.startswith("admin:history:"))
async def show_contact_history(callback: CallbackQuery):
    """Show full contact history"""
    user_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        history = await get_contact_history(session, user_id, limit=20)
        user = await get_user_by_id(session, user_id)
    
    name = user.full_name or user.username or f"ID: {user_id}" if user else f"ID: {user_id}"
    
    text = f"📜 <b>Aloqa tarixi — {name}</b>\n\n"
    
    if not history:
        text += "Hali aloqa bo'lmagan\n"
    else:
        for log in history:
            type_emoji = {"call": "📞", "message": "💬", "meeting": "🤝"}.get(log.contact_type, "📋")
            result_text = {
                "interested": "✅ Qiziqdi",
                "not_interested": "❌ Qiziqmadi",
                "callback": "🔄 Qayta",
                "deal_made": "🤝 Deal!",
                "no_answer": "📵 Javob yo'q"
            }.get(log.result, log.result or "-")
            
            text += (
                f"{type_emoji} {log.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"   Natija: {result_text}\n"
            )
            if log.notes:
                text += f"   📝 {log.notes}\n"
            text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Profil", callback_data=f"crm:user:{user_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ====== BUY REQUESTS LIST ======

@router.message(F.text == "🛒 Olish arizalari")
async def show_buy_requests_message(message: Message):
    """Show pending buy requests"""
    if message.from_user.id not in settings.admin_list:
        return
    await _show_buy_requests(message)


@router.callback_query(F.data == "crm:buy_requests")
async def show_buy_requests_callback(callback: CallbackQuery):
    """Show buy requests from callback"""
    await _show_buy_requests(callback)


async def _show_buy_requests(event):
    """Show all pending buy requests"""
    async with async_session_maker() as session:
        requests = await get_pending_buy_requests(session)
    
    if not requests:
        text = (
            "🛒 <b>OLISH ARIZALARI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Hozircha yangi arizalar yo'q."
        )
    else:
        text = f"🛒 <b>OLISH ARIZALARI — {len(requests)} ta</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for req in requests[:10]:
            urgency_emoji = get_urgency_emoji(req.urgency)
            score_emoji = get_lead_score_emoji(req.lead_score)
            
            text += (
                f"{urgency_emoji} <b>#{req.id}</b> | {score_emoji} Ball: {req.lead_score}\n"
                f"   🏷 {req.brand or '-'} {req.model or 'Barcha'}\n"
            )
            if req.budget_min and req.budget_max:
                text += f"   💰 {req.budget_min:,.0f}-{req.budget_max:,.0f} $\n"
            if req.phone:
                text += f"   📞 {req.phone}\n"
            text += f"   ⏰ {req.created_at.strftime('%d.%m %H:%M')}\n\n"
    
    buttons = []
    if requests:
        for req in requests[:5]:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📋 #{req.id} — {req.brand or '-'} {req.model or '-'}",
                    callback_data=f"crm:buyreq:{req.id}"
                )
            ])
    buttons.append([InlineKeyboardButton(text="◀️ Dashboard", callback_data="crm:refresh")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("crm:buyreq:"))
async def show_buy_request_detail(callback: CallbackQuery):
    """Show buy request detail"""
    request_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        from database.crud import get_buy_request_by_id, find_matching_cars_for_request
        req = await get_buy_request_by_id(session, request_id)
        if not req:
            await callback.answer("❌ Ariza topilmadi", show_alert=True)
            return
        
        user = await get_user_by_id(session, req.user_id)
        matching = await find_matching_cars_for_request(session, req)
    
    urgency_emoji = get_urgency_emoji(req.urgency)
    urgency_text = get_urgency_text(req.urgency)
    
    text = f"🛒 <b>ARIZA #{req.id}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"{urgency_emoji} Ustuvorlik: <b>{urgency_text}</b>\n"
    text += f"📊 Ball: <b>{req.lead_score}/100</b>\n\n"
    
    if user:
        name = user.full_name or user.username or f"ID: {user.telegram_id}"
        text += f"👤 Mijoz: <b>{name}</b>\n"
        if user.username:
            text += f"   📱 @{user.username}\n"
    
    if req.phone:
        text += f"📞 Telefon: <b>{req.phone}</b>\n"
    
    text += f"\n🏷 Brend: <b>{req.brand or '-'}</b>\n"
    text += f"🚙 Model: <b>{req.model or 'Barcha'}</b>\n"
    
    if req.year_from and req.year_to:
        text += f"📅 Yil: <b>{req.year_from}-{req.year_to}</b>\n"
    if req.budget_min and req.budget_max:
        text += f"💰 Budjet: <b>{req.budget_min:,.0f}-{req.budget_max:,.0f} $</b>\n"
    if req.transmission:
        text += f"⚙️ Uzatma: <b>{req.transmission}</b>\n"
    if req.additional_notes:
        text += f"\n📝 Qo'shimcha: {req.additional_notes}\n"
    
    if matching:
        text += f"\n🎯 <b>Mos variantlar: {len(matching)} ta</b>\n"
        for car in matching[:3]:
            text += f"   • {car.brand} {car.model} ({car.year}) — {car.price:,.0f}$\n"
    
    text += f"\n⏰ Ariza: {req.created_at.strftime('%d.%m.%Y %H:%M')}"
    
    await callback.message.edit_text(
        text,
        reply_markup=buy_request_management_keyboard(request_id),
        parse_mode="HTML"
    )
    await callback.answer()


# ====== BLOCK USER ======

@router.callback_query(F.data.startswith("admin:block:"))
async def toggle_block_user(callback: CallbackQuery):
    """Toggle user block"""
    user_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        from database.crud import toggle_user_block
        is_blocked = await toggle_user_block(session, user_id)
    
    if is_blocked is None:
        await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
    elif is_blocked:
        await callback.answer("🚫 Foydalanuvchi bloklandi", show_alert=True)
    else:
        await callback.answer("✅ Blok olib tashlandi", show_alert=True)
    
    # Refresh profile
    callback.data = f"crm:user:{user_id}"
    await show_user_profile(callback)


# ====== ALL USERS ======

@router.callback_query(F.data == "crm:all_users")
async def show_all_users(callback: CallbackQuery):
    """Show all users with scores"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User)
            .where(User.is_admin == False, User.is_blocked == False)
            .order_by(User.lead_score.desc(), User.last_activity.desc())
            .limit(20)
        )
        users = list(result.scalars().all())
    
    text = "👥 <b>BARCHA MIJOZLAR</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, user in enumerate(users, 1):
        name = user.full_name or user.username or f"ID: {user.telegram_id}"
        score_emoji = get_lead_score_emoji(user.lead_score)
        text += f"{i}. {score_emoji} <b>{name}</b> — {user.lead_score} ball\n"
    
    buttons = []
    for user in users[:5]:
        name = user.full_name or user.username or str(user.telegram_id)
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {name[:20]}",
                callback_data=f"crm:user:{user.telegram_id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Dashboard", callback_data="crm:refresh")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()
