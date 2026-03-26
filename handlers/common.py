"""
Common handlers — /start, /help, main menu
Barcha foydalanuvchilar uchun umumiy buyruqlar
"""
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
from loguru import logger

from config import settings
from database.database import async_session_maker
from database.crud import get_or_create_user, is_admin
from keyboards.user_keyboards import main_menu_keyboard, buy_menu_keyboard
from keyboards.admin_keyboards import admin_main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Start command — Botga kirish/ Referral saqlash"""
    await state.clear()
    
    parts = message.text.split(" ")
    if len(parts) > 1:
        payload = parts[1]
        if payload.startswith("ref_"):
            try:
                referrer_id = int(payload.split("_")[1])
                await state.update_data(referred_by_id=referrer_id)
            except ValueError:
                pass
    
    async with async_session_maker() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        # Fast path: check config first, then DB
        user_is_admin = message.from_user.id in settings.admin_list or await is_admin(session, message.from_user.id)
    
    name = message.from_user.first_name or message.from_user.full_name
    hour = datetime.now().hour
    if 6 <= hour < 12:
        greeting = "Xayrli tong"
    elif 12 <= hour < 18:
        greeting = "Xayrli kun"
    elif 18 <= hour < 22:
        greeting = "Xayrli kech"
    else:
        greeting = "Assalomu alaykum"
    
    if user_is_admin:
        text = (
            f"🏠 <b>ADMIN BOSHQARUV PANELI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{greeting}, <b>{name}</b>! 👋\n\n"
            f"📊 <b>Boshqaruv bo'limlari:</b>\n\n"
            f"➕ <b>Moshina qo'shish</b> — yangi e'lon yaratish\n"
            f"📋 <b>Pipeline</b> — sotish jarayonini kuzatish\n"
            f"📥 <b>Murojaatlar</b> — yangi sotish/olish arizalari\n"
            f"🛒 <b>Olish arizalari</b> — xaridorlar ro'yxati\n"
            f"📊 <b>CRM Dashboard</b> — analitika va hisobotlar\n"
            f"🔥 <b>Hot Leads</b> — eng jiddiy mijozlar\n"
            f"📢 <b>Xabar yuborish</b> — barcha foydalanuvchilarga\n"
            f"🔍 <b>Parsing Dashboard</b> — bozor kuzatuvi\n\n"
            f"💡 <i>Oddiy foydalanuvchi rejimiga o'tish uchun pastdagi tugmani bosing</i>"
        )
        await message.answer(text, reply_markup=admin_main_menu_keyboard(), parse_mode="HTML")
    else:
        text = (
            f"🚗 <b>AVTO SAVDO</b> — Moshinalar Oldi-Sotdi Boti\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{greeting}, <b>{name}</b>! 👋\n\n"
            f"Biz sizga eng yaxshi moshinani topishda\n"
            f"va moshinangizni tez sotishda yordam beramiz!\n\n"
            f"📌 <b>Asosiy imkoniyatlar:</b>\n\n"
            f"🚗 <b>Moshina sotib olish</b> — katalog, qidiruv va\n"
            f"     zakazga moshina topish xizmati\n\n"
            f"➕ <b>E'lon berish</b> — moshinangizni bozorga chiqaring\n\n"
            f"🔍 <b>Qidiruv</b> — barcha moshinalar katalogi\n\n"
            f"📊 <b>Narxni baholash</b> — bozor narxini real-time tekshiring\n\n"
            f"📉 <b>Arzon variantlar</b> — bozordan past narxdagi takliflar\n\n"
            f"🔔 <b>Obunalar</b> — yangi e'lonlardan darhol xabardor bo'ling\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📞 Savol bo'lsa: @avtosavdo_admin\n"
            f"📍 Toshkent shahri"
        )
        await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: Message):
    """Yordam — Botning barcha imkoniyatlari"""
    text = (
        "ℹ️ <b>YORDAM — Bot imkoniyatlari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🚗 <b>Moshina sotib olish</b>\n"
        "Bu bo'limda siz moshinalarni o'zingiz qidirishingiz\n"
        "yoki bizga ariza qoldirishingiz mumkin:\n"
        "• <b>Katalog</b> — hamma moshinalarni ko'rish\n"
        "• <b>Qidiruv</b> — filtrlar orqali topish\n"
        "• <b>Ariza qoldirish</b> — mutaxassisga topshirish\n\n"
        
        "➕ <b>E'lon berish</b>\n"
        "Moshinangizni sotishga qo'ying. Rasmlar bilan\n"
        "birga joylang — tezroq buyer topiladi.\n"
        "• Avto Savdo orqali — biz hamma narsani qilamiz\n"
        "• Oddiy e'lon — o'zingiz joylaysiz\n\n"
        
        "🔍 <b>Qidiruv</b>\n"
        "Barcha moshinalar katalogini brend, model,\n"
        "yil va narx bo'yicha filtrlang.\n\n"
        
        "📊 <b>Narxni baholash</b>\n"
        "Moshina brendini, modelini va yilini kiriting —\n"
        "bozordagi haqiqiy narxni, min/max, likvidlikni\n"
        "va sotish tavsiyasini ko'ring.\n\n"
        
        "📉 <b>Arzon variantlar</b>\n"
        "Bozor narxidan past joylashtirilgan e'lonlar.\n"
        "Savdogarlar uchun foydali imkoniyat!\n\n"
        
        "🔔 <b>Obunalar</b>\n"
        "Qidiruv kriteriyalari bo'yicha obuna bo'ling —\n"
        "mening shartlarimga mos yangi e'lon chiqqanda\n"
        "sizga darhol xabar yuboriladi.\n\n"
        
        "❤️ <b>Sevimlilar</b>\n"
        "Yoqtirgan moshinalaringizni saqlab, keyinroq\n"
        "qaytib ko'rishingiz mumkin.\n\n"
        
        "📋 <b>Mening arizalarim</b>\n"
        "Yuborgan olish arizalaringizning holatini\n"
        "real-time kuzatib boring.\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📞 Bog'lanish: @avtosavdo_admin\n"
        "⏰ Ish vaqti: 09:00 — 21:00 (har kuni)\n"
        "📍 Toshkent shahri"
    )
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.message(F.text == "👤 Oddiy foydalanuvchi rejimi")
async def switch_to_user_mode(message: Message):
    """Admin → Oddiy foydalanuvchi rejimiga o'tish"""
    await message.answer(
        "👤 <b>Oddiy foydalanuvchi rejimiga o'tdingiz</b>\n\n"
        "Admin paneliga qaytish uchun /start buyrug'ini yuboring.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🚗 Moshina sotib olish")
async def buy_menu_handler(message: Message):
    """Moshina sotib olish quyi menyusi"""
    request_text = (
        "🚗 <b>MOSHINA SOTIB OLISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Qanday usulda moshina qidiramiz?\n\n"
        "1️⃣ <b>Katalog</b> — barcha mavjud moshinalarni ko'rib chiqish\n"
        "2️⃣ <b>Qidiruv</b> — brend, narx va yil bo'yicha filtrlash\n"
        "3️⃣ <b>Ariza qoldirish</b> — siz xohlagan moshinani biz topib beramiz\n"
        "   (Zakazga moshina topish xizmati)"
    )
    await message.answer(request_text, reply_markup=buy_menu_keyboard(), parse_mode="HTML")


@router.message(F.text == "◀️ Ortga")
async def back_to_main_menu_msg(message: Message):
    """Bosh menyuga qaytish (matnli tugma orqali)"""
    await message.answer("🏠 <b>Bosh menyu</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Bosh menyuga qaytish"""
    await state.clear()
    await callback.message.answer(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """No-op — o'chirilgan tugmalar uchun"""
    await callback.answer()
