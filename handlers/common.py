"""
Common handlers for all users
"""
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import settings
from database.database import async_session_maker
from database.crud import get_or_create_user, is_admin
from keyboards.user_keyboards import main_menu_keyboard
from keyboards.admin_keyboards import admin_main_menu_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    # Register or update user
    async with async_session_maker() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        # DEBUG LOGS
        logger.info(f"USER ID: {message.from_user.id}")
        logger.info(f"ADMIN LIST: {settings.admin_list}")
        
        # Super simple check
        user_is_admin = message.from_user.id in settings.admin_list
        logger.info(f"IS ADMIN: {user_is_admin}")
    
    # Welcome message
    from aiogram.utils.markdown import hbold, hitalic
    
    first_name = message.from_user.first_name
    welcome_text = f"""
👋 <b>Assalomu alaykum, {hbold(first_name)}!</b>

🚀 <b>AvtoSavdo</b> premium avtomobil platformasiga xush kelibsiz!

Biz bilan siz:
✅ <b>Premium katalog</b> — Eng sara avtomobillarni ko'rishingiz
🔍 <b>Intellektual qidiruv</b> — Kerakli moshinani tezda topishingiz
🔔 <b>Avtomatik xabarnoma</b> — Yangi e'lonlardan birinchilardan bo'lib xabardor bo'lishingiz
💵 <b>Tezkor sotuv</b> — O'z avtomobilingizni qulay narxda sotishingiz mumkin

📍 <i>Barcha narxlar <b>USD ($)</b> valyutasida ko'rsatiladi.</i>

Davom etish uchun quyidagi menyudan foydalaning 👇
"""
    
    try:
        if user_is_admin:
            welcome_text += "\n🔑 <b>Siz admin sifatida tizimga kirdingiz.</b>"
            await message.answer(welcome_text, reply_markup=admin_main_menu_keyboard(), parse_mode="HTML")
        else:
            await message.answer(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
        logger.info(f"Welcome message sent to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error sending welcome message to {message.from_user.id}: {e}")
        # Fallback without HTML
        await message.answer("Assalomu alaykum! Xush kelibsiz.", reply_markup=main_menu_keyboard())


@router.message(F.text == "ℹ️ Yordam")
async def help_handler(message: Message):
    """Help command handler"""
    help_text = """
📖 <b>FOYDALANISH QO'LLANMASI</b>

🧭 <b>Botning asosiy bo'limlari:</b>

🚗 <b>Katalog</b> — Mavjud barcha avtomobillarni ko'zdan kechirish.
🔍 <b>Qidiruv</b> — Marka, model, yil va narx bo'yicha saralash.
🔔 <b>Obuna</b> — Sizga kerakli avtomobil paydo bo'lganda bot sizga xabar yuboradi.
💰 <b>Mashina sotish</b> — Avtomobilingiz haqida ma'lumot qoldiring, biz uni sotishda yordam beramiz.

💵 <b>Eslatma:</b> Barcha savdolar va hisob-kitoblar <b>USD ($)</b> kursida amalga oshiriladi.

📞 <b>Texnik yordam:</b> @avtosavdo_admin
🌐 <b>Saytimiz:</b> avtosavdo.uz

<i>Bizni tanlaganingiz uchun rahmat!</i>
"""
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text.in_(["🏠 Bosh menyu", "🏠 Asosiy menuga qaytish", "❌ Bekor qilish", "◀️ Orqaga"]))
async def back_to_main_menu_text(message: Message, state: FSMContext):
    """Return to main menu via text button"""
    await state.clear()
    user_is_admin = message.from_user.id in settings.admin_list
    
    if user_is_admin:
        await message.answer("🔑 Admin bosh menyusi", reply_markup=admin_main_menu_keyboard())
    else:
        await message.answer("🏠 Bosh menyu", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Return to main menu"""
    await state.clear()
    
    user_is_admin = callback.from_user.id in settings.admin_list
    
    # Delete previous message to "switch" menus cleanly
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except Exception:
        pass
        
    if user_is_admin:
        await bot.send_message(
            callback.message.chat.id,
            "🔑 Admin bosh menyusi",
            reply_markup=admin_main_menu_keyboard()
        )
    else:
        await bot.send_message(
            callback.message.chat.id,
            "🏠 Bosh menyu",
            reply_markup=main_menu_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "need_phone")
async def need_phone_handler(callback: CallbackQuery):
    """Handler for when user needs to provide phone"""
    await callback.answer(
        "Bog'lanish uchun avval telefon raqamingizni yuboring",
        show_alert=True
    )
