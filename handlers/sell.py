"""
Handlers for selling cars
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

router = Router()

@router.message(F.text.in_(["🚗 Mashina sotish", "➕ E'lon berish"]))
async def start_car_sell(message: Message, state: FSMContext):
    await state.set_state(CarSellStates.choosing_method)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Avto Savdo yordamida", callback_data="sell_avtosavdo")],
        [InlineKeyboardButton(text="📝 Shunchaki e'lon berish (10,000 so'm)", callback_data="sell_ad")]
    ])
    
    await message.answer(
        "👋 <b>Moshinangizni sotmoqchimisiz?</b>\n\n"
        "Qaysi yo'l bilan sotish senga qulayroq?\n\n"
        "1️⃣ <b>Avto Savdo orqali</b> — Biz hamma ishni o'zimiz qilamiz, tezda mijozi chiqadi.\n"
        "2️⃣ <b>Oddiy e'lon</b> — Botga e'lon qo'yib qo'yasan, mijozlar o'zi yozadi.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "sell_ad")
async def sell_ad_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Send invoice for ad payment"""
    if not settings.payment_provider_token:
        await callback.message.edit_text(
            "⚠️ Uzr akajon, to'lov tizimida nimadir xato.\n"
            "Admin bilan gaplashib yuboring-chi: @avtosavdo_admin"
        )
        return

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="E'lon uchun to'lov",
        description="Moshinangni botga qo'yganing uchun 10 ming so'm xolos.",
        payload="car_ad_payment",
        provider_token=settings.payment_provider_token,
        currency="UZS",
        prices=[LabeledPrice(label="E'lon", amount=1000000)], # 10,000.00 UZS
        start_parameter="car_ad_payment"
    )
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Answer pre-checkout query"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    """Handle successful payment and start ad details collection"""
    await state.set_state(CarSellStates.waiting_brand)
    await message.answer(
        "✅ <b>To'lov o'tdi! Baraka toping.</b>\n\n"
        "Endi moshinani ma'lumotlarini qoldirsangiz bo'ldi.\n"
        "🏷 <b>Moshina markasi nima?</b>\n"
        "<i>(Masalan: Chevrolet, Hyundai, Lada...)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@router.callback_query(F.data == "sell_avtosavdo")
async def sell_avtosavdo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CarSellStates.waiting_brand)
    await callback.message.edit_text(
        "🏢 <b>Avto Savdo bilan sotamiz (Mutlaqo tekin)</b>\n\n"
        "Ma'lumotlarni to'ldiring, mutaxassislarimiz moshizni 'ko'rib' berishadi.\n\n"
        "🏷 <b>Moshina markasini yozing:</b>\n"
        "<i>(Masalan: Chevrolet, BMW, KIA)</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CarSellStates.waiting_brand)
async def process_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await state.set_state(CarSellStates.waiting_model)
    await message.answer("🚘 <b>Modelini ham ayting:</b>\n<i>(Masalan: Gentra, Malibu, Nexia 3)</i>", parse_mode="HTML")

@router.message(CarSellStates.waiting_model)
async def process_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(CarSellStates.waiting_year)
    await message.answer("📅 <b>Yili nechanchi?</b>\n<i>(Faqat yilini yozing, masalan: 2022)</i>", parse_mode="HTML")

@router.message(CarSellStates.waiting_year)
async def process_year(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (1950 <= int(message.text) <= 2025):
        return await message.answer("❌ <b>Yilni to'g'ri kiriting-da akajon:</b>", parse_mode="HTML")
    
    await state.update_data(year=message.text)
    await state.set_state(CarSellStates.waiting_mileage)
    await message.answer("🛣 <b>Probegi qancha yurgan? (km):</b>\n<i>(Masalan: 45000)</i>", parse_mode="HTML")

@router.message(CarSellStates.waiting_mileage)
async def process_mileage(message: Message, state: FSMContext):
    await state.update_data(mileage=message.text)
    await state.set_state(CarSellStates.waiting_engine)
    await message.answer("🔌 <b>Motor hajmi qanaqa?</b>\n<i>(Masalan: 1.5 turbo, 2.0 yoki litrda yozing)</i>", parse_mode="HTML")

@router.message(CarSellStates.waiting_engine)
async def process_engine(message: Message, state: FSMContext):
    await state.update_data(engine=message.text)
    await state.set_state(CarSellStates.waiting_gearbox)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Mexanika"), KeyboardButton(text="Avtomat")],
        [KeyboardButton(text="Variator"), KeyboardButton(text="Robot")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("⚙️ <b>Karobkasi qanaqa?</b>", reply_markup=keyboard, parse_mode="HTML")

@router.message(CarSellStates.waiting_gearbox)
async def process_gearbox(message: Message, state: FSMContext):
    await state.update_data(gearbox=message.text)
    await state.set_state(CarSellStates.waiting_fuel)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Benzin"), KeyboardButton(text="Gaz (Metan)")],
        [KeyboardButton(text="Gaz (Propan)"), KeyboardButton(text="Dizel")],
        [KeyboardButton(text="Elektr"), KeyboardButton(text="Gibrid")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("⛽️ <b>Nimada yuradi (yoqilg'i)?</b>", reply_markup=keyboard, parse_mode="HTML")

@router.message(CarSellStates.waiting_fuel)
async def process_fuel(message: Message, state: FSMContext):
    await state.update_data(fuel=message.text)
    await state.set_state(CarSellStates.waiting_color)
    await message.answer("🎨 <b>Rangi qanaqa?</b>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

@router.message(CarSellStates.waiting_color)
async def process_color(message: Message, state: FSMContext):
    await state.update_data(color=message.text)
    await state.set_state(CarSellStates.waiting_description)
    await message.answer("📝 <b>Moshina haqida batafsil yozing (kraskasi, holati, qo'shimcha jihozlari bormi?):</b>", parse_mode="HTML")

@router.message(CarSellStates.waiting_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CarSellStates.waiting_price)
    await message.answer("💰 <b>Qancha so'rayapsiz ($ dollarda)?</b>\n<i>(Faqat sonini yozing, masalan: 12500)</i>", parse_mode="HTML")

@router.message(CarSellStates.waiting_price)
async def process_price(message: Message, state: FSMContext):
    price_str = re.sub(r'[^\d]', '', message.text)
    if not price_str:
        return await message.answer("❌ <b>Narxni faqat sonda kiriting-da:</b>", parse_mode="HTML")
        
    await state.update_data(price=int(price_str))
    await state.update_data(photos=[])
    await state.set_state(CarSellStates.waiting_photos)
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Tayyor!")],
        [KeyboardButton(text="🗑 Rasmlarni boshidan yuklash")]
    ], resize_keyboard=True)
    
    await message.answer(
        "📸 <b>Moshina rasmlarini yuboring:</b>\n\n"
        "Bir nechta rasm yuboring, moshizni hamma joyi ko'rinsin. "
        "Yuborib bo'lgach, <b>'✅ Tayyor!'</b> tugmasini bosing.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.message(CarSellStates.waiting_photos, F.text == "🗑 Rasmlarni boshidan yuklash")
async def reset_photos(message: Message, state: FSMContext):
    await state.update_data(photos=[])
    await message.answer("Rasmlar o'chirildi. Qaytadan yuboring:")

@router.message(CarSellStates.waiting_photos, F.photo)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    
    await message.answer(f"✅ Rasm olindi! Jami: {len(photos)} ta. Yana yuboring yoki 'Tayyor' tugmasini bosing.")

@router.message(CarSellStates.waiting_photos, F.text == "✅ Tayyor!")
async def photos_done(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get('photos'):
        return await message.answer("❌ Hech bo'lmasa bitta rasm yuboring akajon!")
    
    await state.set_state(CarSellStates.waiting_phone)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="◀️ Orqaga")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("📞 <b>Siz bilan bog'lanish uchun telefon raqamizni qoldiring:</b>", reply_markup=keyboard, parse_mode="HTML")

@router.message(CarSellStates.waiting_phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Orqaga":
        await state.set_state(CarSellStates.waiting_photos)
        return await message.answer("Rasmlarni yuborishda davom eting:")

    phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    
    # --- SAVE TO DATABASE ---
    from database.database import async_session_maker
    from database.crud import create_inquiry
    async with async_session_maker() as session:
        await create_inquiry(
            session,
            user_id=message.from_user.id,
            inquiry_type="sell",
            brand=data['brand'],
            model=data['model'],
            year=int(data['year']),
            price=float(data['price']),
            description=f"🛣 Probeg: {data.get('mileage', 'N/A')} km\n"
                        f"🔌 Motor: {data.get('engine', 'N/A')}\n"
                        f"⚙️ Karobka: {data.get('gearbox', 'N/A')}\n"
                        f"⛽️ Yoqilg'i: {data.get('fuel', 'N/A')}\n"
                        f"🎨 Rangi: {data.get('color', 'N/A')}\n\n"
                        f"📝 {data.get('description', '')}",
            images={'gallery': data.get('photos', [])},
            status="pending"
        )

    # Format professional text for admins
    admin_text = f"""
🆕 <b>SOTUV ARIZASI (YANGI)</b>

👤 <b>Mijoz:</b> {phone}
👤 <b>Telegram:</b> {message.from_user.full_name}

🚘 Model: <b>{data['brand']} {data['model']}</b>
📅 Yili: <b>{data['year']}</b>
🛣 Probeg: <b>{data.get('mileage', 'N/A')} km</b>
🔌 Motor: <b>{data.get('engine', 'N/A')}</b>
⚙️ Karobka: <b>{data.get('gearbox', 'N/A')}</b>
⛽️ Yoqilg'i: <b>{data.get('fuel', 'N/A')}</b>
🎨 Rangi: <b>{data.get('color', 'N/A')}</b>
💰 Narxi: <b>{data['price']:,.0f} $</b>

📝 <b>Tavsif:</b> <i>{data.get('description', 'N/A')}</i>
"""
    
    photos = data.get('photos', [])
    from config import settings
    for admin_id in settings.admin_list:
        try:
            if photos:
                if len(photos) > 1:
                    from aiogram.types import InputMediaPhoto
                    media = [InputMediaPhoto(media=photos[0], caption=admin_text, parse_mode="HTML")]
                    for ph in photos[1:10]: # Max 10 per media group
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
        "✅ <b>Bo'ldi, arizangiz ketti!</b>\n\n"
        "Barcha ma'lumotlar saqlandi. Adminlarimiz ko'rib chiqib, o'zlari sizga telefon qilishadi.\n"
        "E'loningiz holatini <b>'Mening e'lonlarim'</b> bo'limida ko'rishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


# --- MY ADS HANDLER ---
from keyboards.user_keyboards import main_menu_keyboard

@router.message(F.text == "📝 Mening e'lonlarim")
async def show_my_ads(message: Message):
    from database.database import async_session_maker
    from database.crud import get_user_inquiries
    
    async with async_session_maker() as session:
        ads = await get_user_inquiries(session, message.from_user.id)
    
    if not ads:
        return await message.answer("Sizda hozircha e'lonlar yo'q. Birorta moshina sotmoqchimisiz? 😊")

    for ad in ads:
        status_emoji = {"pending": "⏳", "processing": "⚙️", "completed": "✅", "rejected": "❌"}.get(ad.status, "❓")
        text = f"{status_emoji} **E'lon ID: {ad.id}**\n"
        text += f"🚘 {ad.brand} {ad.model} ({ad.year})\n"
        text += f"💰 Narxi: {ad.price:,.0f} $\n"
        text += f"📊 Holati: {ad.status.upper()}\n"
        
        keyboard = None
        if ad.status == "pending":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_ad:{ad.id}")]
            ])
            
        await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("delete_ad:"))
async def delete_my_ad(callback: CallbackQuery):
    ad_id = int(callback.data.split(":")[1])
    from database.database import async_session_maker
    from database.crud import delete_inquiry
    
    async with async_session_maker() as session:
        await delete_inquiry(session, ad_id)
        
    await callback.answer("E'lon o'chirildi 🗑")
    await callback.message.delete()
