"""
Analytics — Statistika va hisobotlar
Admin va foydalanuvchi uchun turli statistik ma'lumotlar
"""
from aiogram import Router, F
from aiogram.types import Message

from config import settings
from database.database import async_session_maker
from database.crud import get_admin_dashboard_stats, get_cars
from keyboards.admin_keyboards import admin_main_menu_keyboard
from keyboards.user_keyboards import main_menu_keyboard

router = Router()


@router.message(F.text.in_(["📊 Statistika", "📊 Hisobotlar"]))
async def show_analytics(message: Message):
    """Statistika — admin va foydalanuvchi"""
    is_admin = message.from_user.id in settings.admin_list
    
    async with async_session_maker() as session:
        stats = await get_admin_dashboard_stats(session)
    
    if is_admin:
        text = (
            "📊 <b>ADMIN STATISTIKA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
            f"🟢 Faol (7 kun): <b>{stats['active_users_7d']}</b>\n"
            f"🆕 Yangi (30 kun): <b>{stats['new_users_30d']}</b>\n"
            f"🔥 Hot leads: <b>{stats['hot_leads']}</b>\n\n"
            f"🚗 Aktiv moshinalar: <b>{stats['total_cars']}</b>\n\n"
            "📥 <b>Kutilayotgan arizalar:</b>\n"
            f"   📝 Sotuv arizalari: <b>{stats['pending_inquiries']}</b>\n"
            f"   🛒 Olish arizalari: <b>{stats['pending_buy_requests']}</b>\n\n"
            f"💰 <b>Sotuvlar (30 kun):</b>\n"
            f"   🏆 Sotilgan: <b>{stats['sold_30d']} ta</b>\n"
            f"   💵 Foyda: <b>{stats['profit_30d']:,.0f} $</b>\n\n"
            "📈 <i>Batafsil hisobotlar uchun\n"
            "📊 CRM Dashboard bo'limiga o'ting</i>"
        )
        await message.answer(text, reply_markup=admin_main_menu_keyboard(), parse_mode="HTML")
    else:
        text = (
            "📊 <b>BOT STATISTIKASI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚗 Katalogdagi moshinalar: <b>{stats['total_cars']}</b>\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n\n"
            "📈 <i>Bozor narxlarini bilish uchun\n"
            "📊 Narxni baholash bo'limiga o'ting</i>"
        )
        await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
