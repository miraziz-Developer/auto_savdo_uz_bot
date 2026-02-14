"""
Sell handler — E'lon berish / Moshina sotish
Klient moshinasi haqida batafsil ma'lumot yig'adi va admin'ga yuboradi
"""
import re
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    LabeledPrice, PreCheckoutQuery, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from loguru import logger

from states.sell import CarSellStates
from config import settings
from keyboards.user_keyboards import main_menu_keyboard
SS
router = Router()


@router.message(F.text.in_(["🚗 Mashina sotish", "➕ E'lon berish"]))
async def start_car_sell(message: Message, state: FSMContext):
    """E'lon berish — 2 ta variant"""
    await state.set_state(CarSellStates.choosing_method)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Avto Savdo orqali (bepul)", callback_data="sell_avtosavdo")],
        [InlineKeyboardButton(text="📝 Oddiy e'lon (10,000 so'm)", callback_data="sell_ad")]
    ])
    
    await message.answer(
        "🚗 <b>MOSHINANGIZNI SOTISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Qaysi usulda sotishni xohlaysiz?\n\n"
        "🏢 <b>Avto Savdo orqali</b>\n"
        "Biz moshinangizni ko'rib chiqamiz, rasmini olamiz,\n"
        "sifatli e'lon tayyorlaymiz va kanal orqali sotamiz.\n"
        "Siz uchun <b>mutlaqo bepul!</b>\n\n"
        "📝 <b>Oddiy e'lon</b>\n"
        "O'zingiz ma'lumotlarni to'ldirasiz va botga joylaysiz.\n"
        "Narxi atigi <b>10,000 so'm</b>.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "sell_ad")
async def sell_ad_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """E'lon uchun to'lov"""
    if not settings.payment_provider_token:
        await callback.message.edit_text(
            "⚠️ <b>Uzr, to'lov tizimida texnik nosozlik</b>\n\n"
            "Iltimos, admin bilan bog'laning: @avtosavdo_admin\n"
            "Yoki «Avto Savdo orqali» usulini tanlang — u bepul!",
            parse_mode="HTML"
        )
        return
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="E'lon joylash uchun to'lov",
        description="Moshinangizni botga joylash — 10,000 so'm",
        payload="car_ad_payment",
        provider_token=settings.payment_provider_token,
        currency="UZS",
        prices=[LabeledPrice(label="E'lon", amount=1000000)],
        start_parameter="car_ad_payment"
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """To'lov oldi tekshiruvi"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    """To'lov muvaffaqiyatli — ma'lumot yig'ishni boshlash"""
    await state.set_state(CarSellStates.waiting_brand)
    await message.answer(
        "✅ <b>To'lov muvaffaqiyatli o'tdi!</b>\n\n"
        "Endi moshinangiz haqida ma'lumot kiriting.\n\n"
        "🏷 <b>Moshina markasini yozing:</b>\n"
        "<i>Masalan: Chevrolet, Hyundai, Toyota</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )


@router.callback_query(F.data == "sell_avtosavdo")
async def sell_avtosavdo_start(callback: CallbackQuery, state: FSMContext):
    """Avto Savdo orqali sotish"""
    await state.set_state(CarSellStates.waiting_brand)
    await callback.message.edit_text(
        "🏢 <b>AVTO SAVDO ORQALI SOTISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Mutaxassislarimiz moshinangizni ko'rib chiqadi,\n"
        "sifatli rasm oladi va kanal orqali sotadi.\n\n"
        "Endi ma'lumotlarni to'ldiring:\n\n"
        "🏷 <b>Moshina markasini yozing:</b>\n"
        "<i>Masalan: Chevrolet, BMW, KIA</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CarSellStates.waiting_brand)
async def process_brand(message: Message, state: FSMContext):
    """Marka qabul qilish"""
    brand = message.text.strip()
    if len(brand) < 2 or len(brand) > 50:
        return await message.answer(
            "❌ Markani to'g'ri kiriting (2-50 belgi)",
            parse_mode="HTML"
        )
    
    await state.update_data(brand=brand)
    await state.set_state(CarSellStates.waiting_model)
    await message.answer(
        f"✅ Marka: <b>{brand}</b>\n\n"
        "🚙 <b>Model nomini kiriting:</b>\n"
        "<i>Masalan: Gentra, Malibu, Nexia 3, Camry</i>",
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_model)
async def process_model(message: Message, state: FSMContext):
    """Model qabul qilish"""
    model = message.text.strip()
    await state.update_data(model=model)
    await state.set_state(CarSellStates.waiting_year)
    await message.answer(
        f"✅ Model: <b>{model}</b>\n\n"
        "📅 <b>Necha yilgi?</b>\n"
        "<i>Faqat yilni yozing: 2022</i>",
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_year)
async def process_year(message: Message, state: FSMContext):
    """Yil qabul qilish"""
    if not message.text.isdigit() or not (1950 <= int(message.text) <= 2026):
        return await message.answer(
            "❌ <b>Yilni to'g'ri kiriting</b>\n"
            "<i>1950 dan 2026 gacha (masalan: 2021)</i>",
            parse_mode="HTML"
        )
    
    await state.update_data(year=message.text)
    await state.set_state(CarSellStates.waiting_mileage)
    await message.answer(
        f"✅ Yili: <b>{message.text}</b>\n\n"
        "🛣 <b>Probegi qancha? (km)</b>\n"
        "<i>Masalan: 45000</i>",
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_mileage)
async def process_mileage(message: Message, state: FSMContext):
    """Probeg qabul qilish"""
    await state.update_data(mileage=message.text)
    await state.set_state(CarSellStates.waiting_engine)
    await message.answer(
        "🔌 <b>Motor hajmi qancha?</b>\n"
        "<i>Masalan: 1.5, 2.0 turbo, 1.8</i>",
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_engine)
async def process_engine(message: Message, state: FSMContext):
    """Motor hajmi qabul qilish"""
    await state.update_data(engine=message.text)
    await state.set_state(CarSellStates.waiting_gearbox)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚙️ Mexanika"), KeyboardButton(text="⚙️ Avtomat")],
        [KeyboardButton(text="⚙️ Variator"), KeyboardButton(text="⚙️ Robot")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(
        "⚙️ <b>Uzatmalar qutisi (karobka)?</b>\n"
        "Quyidagilardan tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_gearbox)
async def process_gearbox(message: Message, state: FSMContext):
    """Karobka qabul qilish"""
    gearbox = message.text.replace("⚙️ ", "")
    await state.update_data(gearbox=gearbox)
    await state.set_state(CarSellStates.waiting_fuel)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⛽ Benzin"), KeyboardButton(text="⛽ Gaz (Metan)")],
        [KeyboardButton(text="⛽ Gaz (Propan)"), KeyboardButton(text="⛽ Dizel")],
        [KeyboardButton(text="⛽ Elektr"), KeyboardButton(text="⛽ Gibrid")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(
        "⛽ <b>Yoqilg'i turi?</b>\n"
        "Quyidagilardan tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_fuel)
async def process_fuel(message: Message, state: FSMContext):
    """Yoqilg'i turi"""
    fuel = message.text.replace("⛽ ", "")
    await state.update_data(fuel=fuel)
    await state.set_state(CarSellStates.waiting_color)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⬜ Oq"), KeyboardButton(text="⬛ Qora")],
        [KeyboardButton(text="🩶 Kumush"), KeyboardButton(text="🔵 Ko'k")],
        [KeyboardButton(text="🔴 Qizil"), KeyboardButton(text="🟤 Boshqa rang")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(
        "🎨 <b>Rangi qanday?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_color)
async def process_color(message: Message, state: FSMContext):
    """Rang qabul qilish"""
    color = message.text.replace("⬜ ", "").replace("⬛ ", "").replace("🩶 ", "").replace("🔵 ", "").replace("🔴 ", "").replace("🟤 ", "")
    await state.update_data(color=color)
    await state.set_state(CarSellStates.waiting_description)
    await message.answer(
        "📝 <b>Moshina haqida batafsil yozing:</b>\n\n"
        "Quyidagilarni yozib bering:\n"
        "• Kraskasi bormi?\n"
        "• Holati qanday?\n"
        "• Qo'shimcha jihozlari (kamera, lyuk, issiqlik va h.k.)\n"
        "• DTP bo'lganmi?\n"
        "• Nima uchun sotyapsiz?",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_description)
async def process_description(message: Message, state: FSMContext):
    """Tavsif qabul qilish"""
    await state.update_data(description=message.text)
    await state.set_state(CarSellStates.waiting_price)
    await message.answer(
        "💰 <b>Qancha narx qo'ymoqchisiz? (dollarda)</b>\n\n"
        "<i>Faqat raqamni yozing, masalan: 12500</i>\n\n"
        "💡 Tip: Real narx qo'ysangiz, tezroq sotiladi!",
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_price)
async def process_price(message: Message, state: FSMContext):
    """Narx qabul qilish"""
    price_str = re.sub(r'[^\d]', '', message.text)
    if not price_str:
        return await message.answer(
            "❌ <b>Narxni faqat raqamda kiriting</b>\n"
            "<i>Masalan: 12500</i>",
            parse_mode="HTML"
        )
    
    price = int(price_str)
    if price < 100 or price > 999999:
        return await message.answer(
            "❌ <b>Narx 100$ dan 999,999$ gacha bo'lishi kerak</b>",
            parse_mode="HTML"
        )
    
    await state.update_data(price=price)
    await state.update_data(photos=[])
    await state.set_state(CarSellStates.waiting_photos)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Tayyor!")],
        [KeyboardButton(text="🗑 Rasmlarni boshidan yuklash")]
    ], resize_keyboard=True)
    
    await message.answer(
        f"✅ Narx: <b>{price:,} $</b>\n\n"
        "📸 <b>Endi moshinaning rasmlarini yuboring:</b>\n\n"
        "📌 <b>Tavsiyalar:</b>\n"
        "• Old tomondan 1 ta\n"
        "• Yon tomondan 2 ta\n"
        "• Orqa tomondan 1 ta\n"
        "• Salon ichidan 2 ta\n"
        "• Motor bo'limi 1 ta\n\n"
        "Rasmlarni yuborib bo'lgach <b>✅ Tayyor!</b> tugmasini bosing.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_photos, F.text == "🗑 Rasmlarni boshidan yuklash")
async def reset_photos(message: Message, state: FSMContext):
    """Rasmlarni tozalash"""
    await state.update_data(photos=[])
    await message.answer(
        "🗑 Rasmlar tozalandi.\n"
        "Qaytadan rasm yuboring:",
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_photos, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Rasm qabul qilish"""
    data = await state.get_data()
    photos = data.get('photos', [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    
    if len(photos) < 3:
        await message.answer(
            f"✅ Rasm qabul qilindi! (Jami: <b>{len(photos)}</b> ta)\n"
            f"Yana yuboring — kamida <b>3 ta</b> rasm bo'lsa yaxshi.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"✅ Rasm qabul qilindi! (Jami: <b>{len(photos)}</b> ta)\n"
            "Yana yuborishingiz yoki <b>✅ Tayyor!</b> bosishingiz mumkin.",
            parse_mode="HTML"
        )


@router.message(CarSellStates.waiting_photos, F.text == "✅ Tayyor!")
async def photos_done(message: Message, state: FSMContext):
    """Rasmlar tugadi — telefonga o'tish"""
    data = await state.get_data()
    if not data.get('photos'):
        return await message.answer(
            "❌ <b>Kamida bitta rasm yuboring!</b>\n"
            "Rasmsiz e'lon juda kam ko'riladi.",
            parse_mode="HTML"
        )
    
    await state.set_state(CarSellStates.waiting_phone)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="◀️ Orqaga")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(
        "📞 <b>Telefon raqamingiz</b>\n\n"
        "Qiziquvchilar siz bilan bog'lanishi uchun\n"
        "raqamingizni yuboring.\n\n"
        "💡 <i>Tugmani bosing — avtomatik yuboriladi</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(CarSellStates.waiting_phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    """Telefon qabul qilish va admin'ga yuborish"""
    if message.text == "◀️ Orqaga":
        await state.set_state(CarSellStates.waiting_photos)
        return await message.answer("📸 Rasmlarni yuborishda davom eting:")
    
    phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    
    # --- DATABASE + LEAD SCORING ---
    from database.database import async_session_maker
    from database.crud import (
        create_inquiry, get_user_by_id, update_user_phone,
        schedule_followups_for_inquiry
    )
    from utils.lead_scoring import (
        calculate_inquiry_lead_score, calculate_user_lead_score,
        detect_urgency_keywords, get_urgency_emoji, get_urgency_text,
        get_lead_score_emoji
    )
    
    desc_text = (
        f"🛣 Probeg: {data.get('mileage', 'N/A')} km\n"
        f"🔌 Motor: {data.get('engine', 'N/A')}\n"
        f"⚙️ Karobka: {data.get('gearbox', 'N/A')}\n"
        f"⛽ Yoqilg'i: {data.get('fuel', 'N/A')}\n"
        f"🎨 Rangi: {data.get('color', 'N/A')}\n\n"
        f"📝 {data.get('description', '')}"
    )
    
    async with async_session_maker() as session:
        await update_user_phone(session, message.from_user.id, phone)
        
        user = await get_user_by_id(session, message.from_user.id)
        user_score = user.lead_score if user else 0
        
        score, urgency = calculate_inquiry_lead_score(
            has_phone=True,
            has_budget=bool(data.get('price')),
            has_images=bool(data.get('photos')),
            is_returning=user and user.total_inquiries > 0,
            has_specific_model=True,
            urgency_keywords=detect_urgency_keywords(data.get('description')),
            user_lead_score=user_score
        )
        
        inquiry = await create_inquiry(
            session,
            user_id=message.from_user.id,
            inquiry_type="sell",
            brand=data['brand'],
            model=data['model'],
            year=int(data['year']),
            price=float(data['price']),
            description=desc_text,
            images={'gallery': data.get('photos', [])},
            phone=phone,
            lead_score=score,
            urgency=urgency,
            status="pending"
        )
        
        await schedule_followups_for_inquiry(session, inquiry.id, message.from_user.id)
        await calculate_user_lead_score(session, message.from_user.id)
    
    # --- ADMIN NOTIFICATION ---
    urgency_emoji = get_urgency_emoji(urgency)
    urgency_text = get_urgency_text(urgency)
    score_emoji = get_lead_score_emoji(score)
    
    user_link = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    
    admin_text = (
        f"🆕 <b>YANGI SOTUV ARIZASI #{inquiry.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{urgency_emoji} Ustuvorlik: <b>{urgency_text}</b>\n"
        f"{score_emoji} Lead ball: <b>{score}/100</b>\n\n"
        f"👤 Mijoz: <b>{message.from_user.full_name}</b>\n"
        f"💬 Telegram: {user_link}\n"
        f"📞 Telefon: <b>{phone}</b>\n\n"
        f"🚗 <b>{data['brand']} {data['model']}</b> ({data['year']})\n"
        f"💰 Narxi: <b>{data['price']:,} $</b>\n"
        f"🛣 Probeg: {data.get('mileage', 'N/A')} km\n"
        f"🔌 Motor: {data.get('engine', 'N/A')}\n"
        f"⚙️ Karobka: {data.get('gearbox', 'N/A')}\n"
        f"⛽ Yoqilg'i: {data.get('fuel', 'N/A')}\n"
        f"🎨 Rangi: {data.get('color', 'N/A')}\n\n"
        f"📝 <b>Tavsif:</b>\n<i>{data.get('description', 'N/A')}</i>\n\n"
        f"📸 Rasmlar: <b>{len(data.get('photos', []))} ta</b>"
    )
    
    photos = data.get('photos', [])
    for admin_id in settings.admin_list:
        try:
            if photos:
                if len(photos) > 1:
                    from aiogram.types import InputMediaPhoto
                    media = [InputMediaPhoto(media=photos[0], caption=admin_text, parse_mode="HTML")]
                    for ph in photos[1:10]:
                        media.append(InputMediaPhoto(media=ph))
                    await bot.send_media_group(chat_id=admin_id, media=media)
                else:
                    await bot.send_photo(chat_id=admin_id, photo=photos[0], caption=admin_text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending to admin {admin_id}: {e}")
    
    await state.clear()
    await message.answer(
        "✅ <b>Arizangiz muvaffaqiyatli yuborildi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Ariza raqami: <b>#{inquiry.id}</b>\n"
        f"🚗 {data['brand']} {data['model']} ({data['year']})\n"
        f"💰 Narx: <b>{data['price']:,} $</b>\n\n"
        "Mutaxassislarimiz ko'rib chiqib, siz bilan bog'lanadi.\n"
        "E'loningiz holatini <b>📋 Mening arizalarim</b> bo'limida\n"
        "kuzatishingiz mumkin.\n\n"
        "⏰ O'rtacha javob vaqti: <b>1-2 soat</b>\n"
        "📞 Savol bo'lsa: @avtosavdo_admin",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


# --- MENING E'LONLARIM ---

@router.message(F.text == "📝 Mening e'lonlarim")
async def show_my_ads(message: Message):
    """Foydalanuvchining e'lonlari"""
    from database.database import async_session_maker
    from database.crud import get_user_inquiries
    
    async with async_session_maker() as session:
        ads = await get_user_inquiries(session, message.from_user.id)
    
    if not ads:
        return await message.answer(
            "📝 <b>Sizda hozircha e'lonlar yo'q</b>\n\n"
            "Moshinangizni sotish uchun ➕ E'lon berish\n"
            "tugmasini bosing.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    
    status_map = {
        "pending": "⏳ Kutilmoqda",
        "processing": "⚙️ Ko'rib chiqilmoqda",
        "completed": "✅ Bajarildi",
        "rejected": "❌ Rad etildi"
    }
    
    text = f"📝 <b>MENING E'LONLARIM</b> ({len(ads)} ta)\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for ad in ads:
        status = status_map.get(ad.status, f"❓ {ad.status}")
        text += (
            f"📋 <b>#{ad.id}</b> — {status}\n"
            f"   🚗 {ad.brand} {ad.model} ({ad.year})\n"
            f"   💰 {ad.price:,.0f} $\n"
            f"   📅 {ad.created_at.strftime('%d.%m.%Y')}\n\n"
        )
    
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("delete_ad:"))
async def delete_my_ad(callback: CallbackQuery):
    """E'lonni o'chirish"""
    ad_id = int(callback.data.split(":")[1])
    from database.database import async_session_maker
    from database.crud import delete_inquiry
    
    async with async_session_maker() as session:
        await delete_inquiry(session, ad_id)
    
    await callback.answer("✅ E'lon o'chirildi", show_alert=True)
    await callback.message.delete()
