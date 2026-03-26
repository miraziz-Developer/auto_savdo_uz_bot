"""
Konkurs Handler — 🎁 Konkursda qatnashish
Telegram kanalga va Instagramga obuna bo'lishni tekshiradi.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from loguru import logger

from database.database import async_session_maker
from database.crud import get_konkurs_participant, register_konkurs_participant, is_admin
from config import settings

router = Router()

# Konkurs kanallari (Agar .env da yo'q bo'lsa, tahrirlashingiz mumkin)
KONKURS_CHANNEL_USERNAME = "@REAL_AVTO_ARZON"
KONKURS_CHANNEL_LINK = "https://t.me/REAL_AVTO_ARZON"
INSTAGRAM_LINK = "https://instagram.com/avtosavdo_uz"


def konkurs_subscription_keyboard() -> InlineKeyboardMarkup:
    """Obunalar uchun havola klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Telegram kanal", url=KONKURS_CHANNEL_LINK)],
            [InlineKeyboardButton(text="📸 Instagram sahifa", url=INSTAGRAM_LINK)],
            [InlineKeyboardButton(text="✅ A'zo bo'ldim (Tasdiqlash)", callback_data="check_konkurs")]
        ]
    )


@router.message(F.text == "🎁 Konkurs (G'olib bo'ling!)")
async def konkurs_start_handler(message: Message, bot: Bot):
    """Konkurs tugmasi — Admin, Doimiy a'zo yoki Yangi a'zolikni ajratadi"""
    user_id = message.from_user.id
    
    async with async_session_maker() as session:
        # 1. Admin tekshiruvi
        if await is_admin(session, user_id):
            from keyboards.admin_keyboards import konkurs_management_keyboard
            text = (
                "⚙️ <b>KONKURS BOSHQARUV PANELI</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Admin, ushbu bo'lim orqali konkurs\n"
                "holatini kuzatishingiz va g'oliblarni\n"
                "aniqlashingiz mumkin."
            )
            await message.answer(text, reply_markup=konkurs_management_keyboard(), parse_mode="HTML")
            return

        # 2. Kanalga a'zoligini tekshirish (Qat'iy: har safar tekshiramiz)
        is_subscribed = True
        try:
            member = await bot.get_chat_member(chat_id=KONKURS_CHANNEL_USERNAME, user_id=user_id)
            if member.status in ['left', 'kicked', 'restricted']:
                is_subscribed = False
        except TelegramBadRequest:
            is_subscribed = True # Bot admin bo'lmasa yoki kanal topilmasa (Test uchun ochiq qoldiramiz)

        # 3. Agar kanalga a'zo bo'lsa va oldin ro'yxatdan o'tgan bo'lsa -> Kabinet
        if is_subscribed:
            participant = await get_konkurs_participant(session, user_id)
            if participant:
                from database.crud import get_konkurs_rank
                rank = await get_konkurs_rank(session, participant.score)
                
                bot_me = await bot.get_me()
                ref_link = f"https://t.me/{bot_me.username}?start=ref_{user_id}"
                
                text = (
                    f"💼 <b>KONKURS — SHAXSIY KABINET</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Sizning ishtirokchi raqamingiz:\n"
                    f"🎟 <b>{participant.ticket_number}</b>\n\n"
                    f"👥 Siz taklif qilgan do'stlar: <b>{participant.score} ta</b>\n"
                    f"🏆 Sizning reytingdagi o'rningiz: <b>{rank}-o'rin</b>\n\n"
                    f"🔗 <b>Sizning taklif havolangiz:</b>\n"
                    f"<code>{ref_link}</code>\n\n"
                    f"<i>(Havolani ustiga bosib nusxalang va do'stlaringizga yuboring)</i>"
                )
                await message.answer(text, parse_mode="HTML")
                return

    # 4. Agar obuna bo'lmagan bo'lsa yoki ro'yxatdan o'tmagan bo'lsa -> Obuna/Ro'yxatga olish
    text = (
        "🎁 <b>AVTOMOBIL KONKURSI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Konkursda qatnashish uchun quyidagi\n"
        "tarmoqlarga a'zo bo'lishingiz shart:\n\n"
        "1️⃣ <b>Telegram kanal</b> (yutuq shu yerda o'ynaladi)\n"
        "2️⃣ <b>Instagram sahifa</b>\n\n"
        "Ikkalasiga obuna bo'lgach, pastdagi\n"
        "<b>✅ A'zo bo'ldim</b> tugmasini bosing!"
    )
    await message.answer(text, reply_markup=konkurs_subscription_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin:konkurs:list")
async def admin_list_participants(callback: CallbackQuery):
    """Barcha ishtirokchilar ro'yxati (Liderlar tartibida)"""
    async with async_session_maker() as session:
        from database.crud import get_konkurs_leaderboard
        participants = await get_konkurs_leaderboard(session, limit=50) # Top 50 talik
        
        if not participants:
            await callback.answer("Hali ishtirokchilar yo'q.")
            return

        text = "👥 <b>ISHTIROKCHILAR (Top-50):</b>\n\n"
        for i, p in enumerate(participants):
            user_name = p.user.full_name or p.user.username or "Ishtirokchi"
            text += f"{i+1}. {user_name} — <b>{p.score} ta</b>\n"
        
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "admin:konkurs:leaderboard")
async def admin_push_leaderboard(callback: CallbackQuery, bot: Bot):
    """Liderlarni kanalga yuborish (manual)"""
    await callback.answer("Liderlar jadvali yuborilmoqda...")
    await post_konkurs_leaderboard(bot)


@router.callback_query(F.data == "admin:konkurs:random_winner")
async def admin_random_winners(callback: CallbackQuery):
    """Random g'oliblarni aniqlash (3 ta)"""
    async with async_session_maker() as session:
        from database.crud import get_random_konkurs_winners
        winners = await get_random_konkurs_winners(session, limit=3)
        
        if not winners:
            await callback.answer("Ishtirokchilar yetarli emas.")
            return

        text = "🎲 <b>RANDOM G'OLIBLAR (3 TA):</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, p in enumerate(winners):
            user = p.user
            u_name = user.full_name or "Ishtirokchi"
            contact_info = f"@{user.username}" if user.username else f"ID: <code>{user.telegram_id}</code>"
            text += (
                f"{i+1}. <b>{u_name}</b>\n"
                f"   🎟 Bilet: {p.ticket_number}\n"
                f"   👤 Kontakt: {contact_info}\n"
                f"   🔗 <a href='tg://user?id={user.telegram_id}'>Lichkaga o'tish</a>\n\n"
            )
        
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer("G'oliblar aniqlandi!")


@router.callback_query(F.data == "admin:konkurs:broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery):
    """Kanalga xabar yuborish bo'yicha yo'riqnoma"""
    text = (
        "📢 <b>KANALGA XABAR YUBORISH</b>\n\n"
        "Konkurs natijalarini yoki yangiliklarni\n"
        "kanalga yuborish uchun <b>/konkurs_push</b>\n"
        "buyrug'idan foydalaning (Top-10 liderlar uchun).\n\n"
        "Maxsus matnli xabarlar uchun asosiy admin\n"
        "paneldagi 'Xabar yuborish' bo'limidan foydalaning."
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "check_konkurs")
async def process_konkurs_check(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Obunani tekshirish va ro'yxatga olish"""
    user_id = callback.from_user.id
    
    # 1. Telegram kanalga a'zoligini tekshirish
    try:
        member = await bot.get_chat_member(chat_id=KONKURS_CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['left', 'kicked', 'restricted']:
            await callback.answer(
                "❌ Kechirasiz, Telegram kanalimizga obuna bo'lmagansiz!", 
                show_alert=True
            )
            return
    except TelegramBadRequest as e:
        logger.error(f"Cannot check chat member. Is bot admin in {KONKURS_CHANNEL_USERNAME}? Error: {e}")
        pass

    # 3. Ro'yxatdan o'tkazamiz
    async with async_session_maker() as session:
        # Avval yana bir bor tekshiramiz (Double check to prevent duplicates)
        participant = await get_konkurs_participant(session, user_id)
        if not participant:
            # Referral ID ni statedan olamiz
            data = await state.get_data()
            referred_by_id = data.get("referred_by_id")
            
            participant = await register_konkurs_participant(session, user_id, referred_by_id)
            
            # Tabriklash va Bileti berish
            bot_me = await bot.get_me()
            ref_link = f"https://t.me/{bot_me.username}?start=ref_{user_id}"
            
            success_text = (
                f"🎉 <b>TABRIKLAYMIZ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Siz konkurs shartlarini to'liq bajardingiz\n"
                f"va rasman ishtirokchiga aylandingiz!\n\n"
                f"🎟 Bilet raqamingiz: <b>{participant.ticket_number}</b>\n\n"
                f"👥 Endi do'stlaringizni taklif qilib, reytingda\n"
                f"yuqoriga ko'tariling va yutuq yutish imkoniyatini oshiring!\n\n"
                f"🔗 <b>Sizning havolangiz:</b>\n"
                f"<code>{ref_link}</code>"
            )
            await callback.message.edit_text(success_text, parse_mode="HTML")
            await callback.answer("✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!")
        else:
            await callback.answer(f"Siz allaqachon qatnashyapsiz! Raqamingiz: {participant.ticket_number}", show_alert=True)

async def post_konkurs_leaderboard(bot: Bot):
    """Kanalga TOP-10 ro'yxatini yuborish uchun asinxron funksiya"""
    from database.crud import get_konkurs_leaderboard
    
    async with async_session_maker() as session:
        leaders = await get_konkurs_leaderboard(session)
        if not leaders:
            return  # Hech kim yo'q bo'lsa post qilmaydi
            
        text = (
            f"🏆 <b>KONKURS — TOP-10 LIDERLAR</b> 🏆\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, p in enumerate(leaders):
            medal = medals[i] if i < 10 else f"{i+1}."
            user_name = p.user.full_name or p.user.username or "Ishtirokchi"
            text += f"{medal} <b>{user_name}</b> — {p.score} ta do'st (Bilet: {p.ticket_number})\n"
            
        bot_me = await bot.get_me()
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 <i>Siz ham ishtirok eting va avtomobil yutib oling!</i>\n"
            f"Buning uchun <b>@{bot_me.username}</b> botiga kiring!"
        )
        
        try:
            await bot.send_message(KONKURS_CHANNEL_USERNAME, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Top-10 liderlar post qilinmadi Error: {e}")

@router.message(Command("konkurs_push"))
async def cmd_konkurs_push(message: Message, bot: Bot):
    """Adminlar uchun qo'lda liderlar jadvalini yuborish"""
    async with async_session_maker() as session:
        if await is_admin(session, message.from_user.id):
            await message.answer("🔄 Liderlar jadvali kanalga yuborilmoqda...")
            await post_konkurs_leaderboard(bot)
            await message.answer("✅ Yuborildi!")
        else:
            await message.answer("⚠️ Bu buyruq faqat adminlar uchun!")
