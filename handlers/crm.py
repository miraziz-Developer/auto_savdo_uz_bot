"""
CRM Dashboard for admin analytics and customer management
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from loguru import logger

from config import settings
from database.database import async_session_maker
from database.models import User, Inquiry, Car, Subscription
from sqlalchemy import select, func, and_
from keyboards.admin_keyboards import admin_main_menu_keyboard

router = Router()


async def check_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in settings.admin_list


@router.message(F.text == "📊 CRM Dashboard")
async def show_crm_dashboard(message: Message):
    """Show CRM dashboard"""
    if not await check_admin(message.from_user.id):
        await message.answer("❌ Sizda ushbu buyruqqa ruxsat yo'q")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Mijozlar", callback_data="crm:customers"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="crm:stats")
        ],
        [
            InlineKeyboardButton(text="📥 Murojaatlar", callback_data="crm:inquiries"),
            InlineKeyboardButton(text="🔔 Obunalar", callback_data="crm:subscriptions")
        ],
        [
            InlineKeyboardButton(text="🚗 Mashhur moshinalar", callback_data="crm:popular_cars"),
            InlineKeyboardButton(text="📈 Faollik", callback_data="crm:activity")
        ]
    ])
    
    await message.answer(
        "📊 **CRM Dashboard**\n\n"
        "Mijozlar va biznes analitikasi:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "crm:customers")
async def show_customers(callback: CallbackQuery):
    """Show customer statistics"""
    async with async_session_maker() as session:
        # Total users
        total_result = await session.execute(select(func.count(User.id)))
        total_users = total_result.scalar_one()
        
        # Active users (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_result = await session.execute(
            select(func.count(User.id)).where(User.last_activity >= week_ago)
        )
        active_users = active_result.scalar_one()
        
        # New users (last 30 days)
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_result = await session.execute(
            select(func.count(User.id)).where(User.created_at >= month_ago)
        )
        new_users = new_result.scalar_one()
        
        # Users with phone
        phone_result = await session.execute(
            select(func.count(User.id)).where(User.phone.isnot(None))
        )
        users_with_phone = phone_result.scalar_one()
    
    text = f"""
👥 **Mijozlar Statistikasi**

📊 Jami foydalanuvchilar: {total_users}
✅ Faol (7 kun): {active_users}
🆕 Yangi (30 kun): {new_users}
📱 Telefon bergan: {users_with_phone}

📈 Konversiya: {(users_with_phone/total_users*100):.1f}% 
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Oxirgi foydalanuvchilar", callback_data="crm:recent_users")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="crm:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "crm:recent_users")
async def show_recent_users(callback: CallbackQuery):
    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.last_activity.desc()).limit(10))
        users = result.scalars().all()
    
    await callback.message.answer("👥 **Oxirgi 10 ta foydalanuvchi:**")
    for u in users:
        status = "🔴 BLOKLANGAN" if u.is_blocked else "🟢 FAOL"
        btn_text = "🔓 Unblock" if u.is_blocked else "🚫 Block"
        
        text = f"👤 {u.full_name or u.username or 'No Name'}\nID: `{u.telegram_id}`\nHolati: {status}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data=f"crm:toggle_block:{u.telegram_id}")]
        ])
        await callback.message.answer(text, reply_markup=kb, parse_mode="MARKDOWN")

@router.callback_query(F.data.startswith("crm:toggle_block:"))
async def toggle_block_handler(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[2])
    from database.crud import toggle_user_block
    async with async_session_maker() as session:
        is_blocked = await toggle_user_block(session, user_id)
    
    status = "bloklandi 🚫" if is_blocked else "blokdan ochildi ✅"
    await callback.answer(f"Foydalanuvchi {status}")
    await callback.message.edit_text(callback.message.text.split("\nHolati:")[0] + f"\nHolati: {'🔴 BLOKLANGAN' if is_blocked else '🟢 FAOL'}")

@router.callback_query(F.data == "crm:back")
async def crm_back(callback: CallbackQuery):
    await show_crm_dashboard(callback.message)


@router.callback_query(F.data == "crm:stats")
async def show_crm_stats(callback: CallbackQuery):
    """Show general CRM statistics"""
    async with async_session_maker() as session:
        # Cars statistics
        total_cars = await session.execute(select(func.count(Car.id)))
        available_cars = await session.execute(
            select(func.count(Car.id)).where(Car.is_available == True)
        )
        
        # Inquiries
        pending_inquiries = await session.execute(
            select(func.count(Inquiry.id)).where(Inquiry.status == "pending")
        )
        
        # Subscriptions
        active_subs = await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )
        
        # Most viewed car
        most_viewed = await session.execute(
            select(Car).order_by(Car.views_count.desc()).limit(1)
        )
        top_car = most_viewed.scalar_one_or_none()
    
    text = f"""
📊 **Umumiy Statistika**

🚗 Jami moshinalar: {total_cars.scalar_one()}
✅ Mavjud: {available_cars.scalar_one()}
📥 Kutilayotgan murojaatlar: {pending_inquiries.scalar_one()}
🔔 Faol obunalar: {active_subs.scalar_one()}

"""
    
    if top_car:
        text += f"\n🏆 Eng ko'p ko'rilgan:\n{top_car.brand} {top_car.model} ({top_car.views_count} marta)"
    
    await callback.message.edit_text(text)


@router.callback_query(F.data == "crm:inquiries")
async def show_inquiries_stats(callback: CallbackQuery):
    """Show inquiries statistics"""
    async with async_session_maker() as session:
        # Count by status
        result = await session.execute(
            select(
                Inquiry.status,
                func.count(Inquiry.id).label('count')
            ).group_by(Inquiry.status)
        )
        
        status_counts = {row.status: row.count for row in result.all()}
        
        # Count by type
        type_result = await session.execute(
            select(
                Inquiry.inquiry_type,
                func.count(Inquiry.id).label('count')
            ).group_by(Inquiry.inquiry_type)
        )
        
        type_counts = {row.inquiry_type: row.count for row in type_result.all()}
    
    text = "📥 **Murojaatlar Statistikasi**\n\n"
    text += "**Holat bo'yicha:**\n"
    text += f"⏳ Kutilmoqda: {status_counts.get('pending', 0)}\n"
    text += f"⚙️ Jarayonda: {status_counts.get('processing', 0)}\n"
    text += f"✅ Bajarildi: {status_counts.get('completed', 0)}\n"
    text += f"❌ Rad etildi: {status_counts.get('rejected', 0)}\n\n"
    
    text += "**Turi bo'yicha:**\n"
    text += f"💰 Sotib olish: {type_counts.get('buy', 0)}\n"
    text += f"🚗 Sotish: {type_counts.get('sell', 0)}\n"
    text += f"❓ Savol: {type_counts.get('question', 0)}\n"
    
    await callback.message.edit_text(text)


@router.callback_query(F.data == "crm:subscriptions")
async def show_subscriptions_stats(callback: CallbackQuery):
    """Show subscriptions statistics"""
    async with async_session_maker() as session:
        # Most popular brands
        result = await session.execute(
            select(
                Subscription.brand,
                func.count(Subscription.id).label('count')
            )
            .where(and_(
                Subscription.is_active == True,
                Subscription.brand.isnot(None)
            ))
            .group_by(Subscription.brand)
            .order_by(func.count(Subscription.id).desc())
            .limit(5)
        )
        
        popular_brands = result.all()
    
    text = "🔔 **Obunalar Statistikasi**\n\n"
    text += "**Eng ko'p qidirilayotgan brendlar:**\n\n"
    
    for i, row in enumerate(popular_brands, 1):
        text += f"{i}. {row.brand}: {row.count} ta obuna\n"
    
    if not popular_brands:
        text += "Hozircha ma'lumot yo'q"
    
    await callback.message.edit_text(text)


@router.callback_query(F.data == "crm:popular_cars")
async def show_popular_cars(callback: CallbackQuery):
    """Show most popular cars"""
    async with async_session_maker() as session:
        # Most viewed cars
        result = await session.execute(
            select(Car)
            .where(Car.is_available == True)
            .order_by(Car.views_count.desc())
            .limit(10)
        )
        
        popular_cars = result.scalars().all()
    
    text = "🚗 **Mashhur Moshinalar**\n\n"
    text += "Ko'rishlar bo'yicha TOP-10:\n\n"
    
    for i, car in enumerate(popular_cars, 1):
        text += f"{i}. {car.brand} {car.model} ({car.year})\n"
        text += f"   👁 {car.views_count} ko'rish | 💰 <b>{car.price:,.0f} $</b>\n\n"
    
    await callback.message.edit_text(text)


@router.callback_query(F.data == "crm:activity")
async def show_activity(callback: CallbackQuery):
    """Show recent activity"""
    async with async_session_maker() as session:
        # Recent users
        recent_users = await session.execute(
            select(User)
            .order_by(User.last_activity.desc())
            .limit(5)
        )
        
        users = recent_users.scalars().all()
    
    text = "📈 **So'nggi Faollik**\n\n"
    text += "Oxirgi faol foydalanuvchilar:\n\n"
    
    for user in users:
        name = user.full_name or user.username or f"User {user.telegram_id}"
        activity_time = user.last_activity.strftime('%d.%m %H:%M')
        text += f"👤 {name}\n   📅 {activity_time}\n\n"
    
    await callback.message.edit_text(text)
