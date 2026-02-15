"""
Admin handlers for car management
"""
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import settings
from database.database import async_session_maker
from database.crud import (
    is_admin, create_car, get_cars, get_car_by_id,
    update_car, get_pending_inquiries, update_inquiry_status,
    create_sold_car, convert_inquiry_to_car
)
from keyboards.admin_keyboards import (
    admin_main_menu_keyboard, car_management_keyboard,
    publish_keyboard, inquiry_management_keyboard, statistics_keyboard
)
from keyboards.user_keyboards import main_menu_keyboard, cancel_keyboard, confirm_keyboard
from states.states import AddCarStates, RecordSaleStates, BroadcastStates, AdminConvertStates
from analytics.sales_analytics import SalesAnalytics

router = Router()


async def check_admin(user_id: int) -> bool:
    """Check if user is admin"""
    if user_id in settings.admin_list:
        return True
    
    async with async_session_maker() as session:
        return await is_admin(session, user_id)


@router.message(F.text == "➕ Moshina qo'shish (ADMIN)")
async def start_add_car_menu(message: Message):
    """Start adding new car - Menu"""
    if not await check_admin(message.from_user.id):
        await message.answer("❌ Sizda ushbu buyruqqa ruxsat yo'q")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Qo'lda kiritish", callback_data="add_car:manual")],
        [InlineKeyboardButton(text="📥 Sotuv arizalaridan tanlash", callback_data="add_car:from_inquiry")]
    ])
    
    await message.answer(
        "🚗 <b>YANGI MOSHINA QO'SHISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Qaysi usulda qo'shmoqchisiz?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "add_car:manual")
async def start_add_car_manual(callback: CallbackQuery, state: FSMContext):
    """Start manual add car flow"""
    await callback.message.delete()
    await callback.message.answer(
        "🚗 <b>YANGI MOSHINA QO'SHISH (QO'LDA)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏷 <b>Moshina brendini kiriting:</b>\n"
        "<i>Masalan: Chevrolet, Toyota, BMW</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_brand)
    await callback.answer()

@router.callback_query(F.data == "add_car:from_inquiry")
async def select_inquiry_for_car(callback: CallbackQuery):
    """Select inquiry to convert"""
    async with async_session_maker() as session:
        inquiries = await get_pending_inquiries(session)
    
    if not inquiries:
        await callback.answer("❌ Arizalar topilmadi. Avval 'Murojaatlar' bo'limini tekshiring.", show_alert=True)
        return
        
    kb = []
    for inq in inquiries:
        kb.append([InlineKeyboardButton(
            text=f"{inq.brand} {inq.model} ({inq.year}) - {inq.price}$", 
            callback_data=f"inquiry:convert:{inq.id}"
        )])
    # Add back button logic if needed, or simple close
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="admin:cars:list")]) 
    
    await callback.message.edit_text(
        "📥 <b>Qaysi arizani katalogga o'tkazamiz?</b>\n"
        "Tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )


@router.message(AddCarStates.waiting_for_brand)
async def process_car_brand(message: Message, state: FSMContext):
    """Process car brand"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ <b>Bekor qilindi</b>", reply_markup=admin_main_menu_keyboard(), parse_mode="HTML")
        return
    
    await state.update_data(brand=message.text)
    await message.answer(
        f"✅ Brend: <b>{message.text}</b>\n\n"
        "🚙 <b>Model nomini kiriting:</b>\n"
        "<i>Masalan: Gentra, Camry</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_model)


@router.message(AddCarStates.waiting_for_model)
async def process_car_model(message: Message, state: FSMContext):
    """Process car model"""
    await state.update_data(model=message.text)
    await message.answer(
        f"✅ Model: <b>{message.text}</b>\n\n"
        "📅 <b>Yilini kiriting:</b>\n"
        "<i>Masalan: 2022</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_year)


@router.message(AddCarStates.waiting_for_year)
async def process_car_year(message: Message, state: FSMContext):
    """Process car year"""
    try:
        year = int(message.text)
        await state.update_data(year=year)
        await message.answer("💰 <b>Narxini kiriting (USD da):</b>", parse_mode="HTML")
        await state.set_state(AddCarStates.waiting_for_price)
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri yil kiriting")


@router.message(AddCarStates.waiting_for_price)
async def process_car_price(message: Message, state: FSMContext):
    """Process car price"""
    try:
        price = float(message.text.replace(" ", "").replace(",", ""))
        await state.update_data(price=price)
        await message.answer(
            f"✅ Narx: <b>{price:,.0f} $</b>\n\n"
            "🛣 <b>Probegini kiriting (km):</b>\n"
            "<i>Yoki /skip bosib o'tkazib yuboring</i>",
            parse_mode="HTML"
        )
        await state.set_state(AddCarStates.waiting_for_mileage)
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri narx kiriting", parse_mode="HTML")


@router.message(AddCarStates.waiting_for_mileage)
async def process_car_mileage(message: Message, state: FSMContext):
    """Process car mileage"""
    if message.text != "/skip":
        try:
            mileage = int(message.text.replace(" ", "").replace(",", ""))
            await state.update_data(mileage=mileage)
        except ValueError:
            await message.answer("❌ Iltimos, to'g'ri probeg kiriting")
            return
    
    await message.answer(
        "🎨 <b>Rangini kiriting:</b>\n"
        "<i>Yoki /skip bosing</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_color)


@router.message(AddCarStates.waiting_for_color)
async def process_car_color(message: Message, state: FSMContext):
    """Process car color"""
    if message.text != "/skip":
        await state.update_data(color=message.text)
    
    await message.answer(
        "📝 <b>Tavsifini kiriting:</b>\n"
        "<i>Yoki /skip bosing</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_description)


@router.message(AddCarStates.waiting_for_description)
async def process_car_description(message: Message, state: FSMContext):
    """Process car description"""
    if message.text != "/skip":
        await state.update_data(description=message.text)
    
    await message.answer(
        "📸 <b>Moshina rasmlarini yuboring</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Birinchi yuborilgan rasm — <b>asosiy rasm</b> bo'ladi.\n"
        "Yuborib bo'lgach <b>✅ Tayyor!</b> tugmasini bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Tayyor!")]],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )
    await state.update_data(photos_list=[])
    await state.set_state(AddCarStates.waiting_for_images)


@router.message(AddCarStates.waiting_for_images, F.photo)
async def process_car_images(message: Message, state: FSMContext):
    """Process car images"""
    data = await state.get_data()
    photos = data.get('photos_list', [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos_list=photos)
    
    if len(photos) == 1:
        await message.answer("✅ Asosiy rasm qabul qilindi. Yana rasmlarni yuboravering...")

@router.message(AddCarStates.waiting_for_images, (F.text == "/done") | (F.text == "✅ Tayyor!") | (F.text == "/skip"))
async def process_car_images_done(message: Message, state: FSMContext):
    """Finish image collection"""
    data = await state.get_data()
    photos = data.get('photos_list', [])
    
    if photos:
        await state.update_data(images={
            'main': photos[0],
            'gallery': photos[1:] if len(photos) > 1 else []
        })
    elif message.text == "/skip":
        await state.update_data(images=None)
    else:
        await message.answer("Hech bo'lmasa bitta rasm yuboring yoki /skip bosing.")
        return

    await show_car_confirmation(message, state)


async def show_car_confirmation(message: Message, state: FSMContext):
    """Show car confirmation"""
    data = await state.get_data()
    
    text = (
        "✅ <b>MOSHINA MA'LUMOTLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    text += f"🏷 Brend: <b>{data['brand']}</b>\n"
    text += f"🚙 Model: <b>{data['model']}</b>\n"
    text += f"📅 Yil: <b>{data['year']}</b>\n"
    text += f"💰 Narxi: <b>{data['price']:,.0f} $</b>\n"
    
    if data.get('mileage'):
        text += f"🛣 Probeg: <b>{data['mileage']:,} km</b>\n"
    if data.get('color'):
        text += f"🎨 Rang: <b>{data['color']}</b>\n"
    if data.get('images'):
        photos_count = 1 + len(data['images'].get('gallery', []))
        text += f"📸 Rasmlar: <b>{photos_count} ta</b>\n"
    if data.get('description'):
        text += f"\n📝 Tavsif: <i>{data['description']}</i>\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "✅ Saqlashni tasdiqlaysizmi?"
    
    await message.answer(text, reply_markup=confirm_keyboard("add_car"))
    await state.set_state(AddCarStates.confirm_car)


from utils.notifications import publish_admin_car, notify_matching_users

@router.callback_query(F.data == "confirm:add_car", AddCarStates.confirm_car)
async def confirm_add_car(callback: CallbackQuery, state: FSMContext):
    """Confirm and save car"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        car = await create_car(
            session,
            brand=data['brand'],
            model=data['model'],
            year=data['year'],
            price=data['price'],
            mileage=data.get('mileage'),
            color=data.get('color'),
            description=data.get('description'),
            images=data.get('images')
        )
        
        # Share to admin channel
        car_dict = {
            'brand': data['brand'],
            'model': data['model'],
            'year': data['year'],
            'price': data['price'],
            'color': data.get('color'),
            'description': data.get('description'),
            'images': data.get('images')
        }
        await publish_admin_car(car_dict)
        
        # Notify subscribers
        await notify_matching_users(car.id)
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Moshina muvaffaqiyatli qo'shildi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <b>{car.id}</b>\n"
        f"🚗 {data['brand']} {data['model']} ({data['year']})\n"
        f"💰 Narx: {data['price']:,.0f} $\n\n"
        f"📢 Kanalga ham joylandi!",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML"
    )


# --- CONVERT INQUIRY TO CAR (FLIPPER) ---

@router.callback_query(F.data.startswith("inquiry:convert:"))
async def start_inquiry_conversion(callback: CallbackQuery, state: FSMContext):
    """Start logic to convert inquiry to our car inventory"""
    try:
        inquiry_id = int(callback.data.split(":")[2])
    except:
        await callback.answer("Xatolik ID", show_alert=True)
        return
        
    await state.update_data(inquiry_id=inquiry_id)
    await state.set_state(AdminConvertStates.waiting_for_price)
    
    await callback.message.answer(
        f"🔄 <b>Inquiry #{inquiry_id} ni Katalogga o'tkazish</b>\n\n"
        "Biz bu mashinani nechi pulga sotyapmiz?\n"
        "<i>(Narxni dollarda kiritng, faqat raqam)</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminConvertStates.waiting_for_price)
async def process_conversion_price(message: Message, state: FSMContext):
    """Process price and skip directly to description (auto-extract others)"""
    try:
        price = float(message.text.replace(' ', '').replace(',', '').replace('$', ''))
    except ValueError:
        await message.answer("❌ Iltimos, narxni to'g'ri kiriting (faqat raqam).")
        return
        
    await state.update_data(price=price)
    
    # Get inquiry details
    data = await state.get_data()
    inquiry_id = data.get('inquiry_id')
    
    from database.crud import get_inquiry_by_id
    async with async_session_maker() as session:
        inq = await get_inquiry_by_id(session, inquiry_id)
        if inq:
            desc = inq.description or ""
            
            # Auto-Extract Mileage
            import re
            m_match = re.search(r'Probeg:?\s*(\d[\d\s]*)(km)?', desc, re.IGNORECASE)
            try:
                mileage = int(m_match.group(1).replace(" ", "")) if m_match else 0
            except:
                mileage = 0

            # Auto-Extract Color
            c_match = re.search(r'Rang[ui]?:?\s*([^\n]+)', desc, re.IGNORECASE)
            color = c_match.group(1).strip() if c_match else None
            
            await state.update_data(
                inquiry_desc=desc, 
                inquiry_brand=inq.brand, 
                inquiry_model=inq.model, 
                inquiry_year=inq.year, 
                inquiry_images=inq.images,
                mileage=mileage,
                color=color
            )
            
            await message.answer(
                "📝 <b>Tavsif (Description) ni tahrirlang:</b>\n\n"
                "Hozirgi matnni nusxalab, kerakli joyini o'zgartirib yuboring.\n"
                "Yoki yangi matn yozing.",
                parse_mode="HTML"
            )
            await message.answer(f"<code>{desc}</code>", parse_mode="HTML")
            await state.set_state(AdminConvertStates.waiting_for_description)
        else:
            await message.answer("❌ Xatolik: Inquiry topilmadi.")
            await state.clear()


@router.message(AdminConvertStates.waiting_for_description)
async def process_conversion_desc(message: Message, state: FSMContext):
    desc = message.text
    if desc == "/skip": 
        data = await state.get_data()
        desc = data.get('inquiry_desc', '')
        
    await state.update_data(description=desc)
    
    # Confirm
    data = await state.get_data()
    color_val = data['color'] or "Noma'lum"
    
    text = (
        "✅ <b>YANGI ARIZA -> KATALOG</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚗 Moshina: <b>{data['inquiry_brand']} {data['inquiry_model']}</b> ({data['inquiry_year']})\n"
        f"💰 Narx: <b>{data['price']:,.0f} $</b>\n"
        f"🛣 Probeg: {data['mileage']:,} km\n"
        f"🎨 Rang: {color_val}\n\n"
        f"📝 Tavsif: <i>{desc}</i>\n\n"
        "Tasdiqlaysizmi?"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="convert:confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="convert:cancel")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(AdminConvertStates.confirm_conversion)


@router.callback_query(F.data == "convert:confirm", AdminConvertStates.confirm_conversion)
async def confirm_conversion_final(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    async with async_session_maker() as session:
        try:
            new_car = await convert_inquiry_to_car(
                session,
                inquiry_id=data['inquiry_id'],
                price=data['price'],
                brand=data['inquiry_brand'],
                model=data['inquiry_model'],
                year=data['inquiry_year'],
                description=data['description'],
                images=data['inquiry_images'],
                mileage=data['mileage'],
                color=data['color']
            )
            
            # Publish to Channel automatically? (Optional, maybe ask separately or do it)
            # await publish_admin_car(new_car.to_dict()) # If needed
            
            await callback.message.edit_text(
                f"✅ <b>Muvaffaqiyatli qo'shildi!</b>\n"
                f"ID: {new_car.id}",
                parse_mode="HTML"
            )
            # Show car management menu
            await show_admin_car_details(callback.message, new_car.id)
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            await callback.answer("Xatolik bo'ldi")
            
    await state.clear()


@router.callback_query(F.data == "convert:cancel", AdminConvertStates.confirm_conversion)
async def cancel_conversion(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi")


@router.message(F.text == "📋 Admin: Moshinalar")
async def list_cars_admin(message: Message):
    """List all cars for admin"""
    if not await check_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        cars = await get_cars(session, limit=20)
    
    if not cars:
        await message.answer(
            "🚗 <b>Moshinalar mavjud emas</b>\n"
            "Qo'shish uchun ➕ tugmasini bosing.",
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "🚗 <b>MOSHINALAR RO'YXATI</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    await message.answer(text, parse_mode="HTML")
    
    # Also show detail for individual management (example with first car)
    if cars:
        await show_admin_car_details(message, cars[0].id)

async def show_admin_car_details(message: Message, car_id: int):
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        if car:
            text = f"⚙️ <b>Boshqarish:</b> {car.brand} {car.model} (ID: {car.id})"
            await message.answer(text, reply_markup=car_management_keyboard(car.id), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:car:photo:"))
async def admin_add_photo(callback: CallbackQuery, state: FSMContext):
    """Add photos to existing car"""
    car_id = int(callback.data.split(":")[3])
    await state.update_data(edit_car_id=car_id, photos_list=[])
    await state.set_state(AddCarStates.waiting_for_images)
    await callback.message.answer(
        f"📸 <b>Moshina #{car_id} uchun rasm qo'shing</b>\n\n"
        "Rasmlarni yuboring, keyin ✅ Tayyor! bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Tayyor!")]],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:car:edit:"))
async def admin_edit_car(callback: CallbackQuery):
    """Edit car details"""
    car_id = int(callback.data.split(":")[3])
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        if not car:
            await callback.answer("❌ Moshina topilmadi", show_alert=True)
            return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"edit:price:{car_id}"),
            InlineKeyboardButton(text="📝 Tavsifni o'zgartirish", callback_data=f"edit:desc:{car_id}"),
        ],
        [
            InlineKeyboardButton(text="🎨 Rangni o'zgartirish", callback_data=f"edit:color:{car_id}"),
            InlineKeyboardButton(text="🛣 Probegni o'zgartirish", callback_data=f"edit:mileage:{car_id}"),
        ],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="admin:cars:list")],
    ])
    
    await callback.message.edit_text(
        f"✏️ <b>{car.brand} {car.model} ({car.year}) ni tahrirlash</b>\n\n"
        f"💰 Narx: {car.price:,.0f} $\n"
        f"🛣 Probeg: {car.mileage or 0:,} km\n"
        f"🎨 Rang: {car.color or 'N/A'}\n\n"
        f"Qaysi maydonni o'zgartirmoqchisiz?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit:price:"))
async def edit_car_price(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split(":")[2])
    await state.update_data(edit_car_id=car_id, edit_field="price")
    await state.set_state(AddCarStates.waiting_for_price)
    await callback.message.answer("💰 <b>Yangi narxni kiriting (USD):</b>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("edit:desc:"))
async def edit_car_desc(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split(":")[2])
    await state.update_data(edit_car_id=car_id, edit_field="description")
    await state.set_state(AddCarStates.waiting_for_description)
    await callback.message.answer("📝 <b>Yangi tavsifni yozing:</b>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("edit:color:"))
async def edit_car_color(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split(":")[2])
    await state.update_data(edit_car_id=car_id, edit_field="color")
    await state.set_state(AddCarStates.waiting_for_color)
    await callback.message.answer("🎨 <b>Yangi rangni yozing:</b>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("edit:mileage:"))
async def edit_car_mileage(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split(":")[2])
    await state.update_data(edit_car_id=car_id, edit_field="mileage")
    await state.set_state(AddCarStates.waiting_for_mileage)
    await callback.message.answer("🛣 <b>Yangi probegni kiriting (km):</b>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:car:delete:"))
async def admin_delete_car(callback: CallbackQuery):
    car_id = int(callback.data.split(":")[3])
    async with async_session_maker() as session:
        # Actually delete or mark as unavailable
        car = await get_car_by_id(session, car_id)
        if car:
            car.is_available = False
            await session.commit()
            await callback.answer("❌ Moshina o'chirildi (arxivlandi)")
            await callback.message.delete()
        else:
            await callback.answer("Xatolik: topilmadi")

@router.callback_query(F.data.startswith("admin:car:publish:"))
async def admin_publish_car_menu(callback: CallbackQuery):
    car_id = int(callback.data.split(":")[3])
    await callback.message.edit_reply_markup(reply_markup=publish_keyboard(car_id))

@router.callback_query(F.data.startswith("publish:telegram:"))
async def admin_publish_telegram(callback: CallbackQuery):
    car_id = int(callback.data.split(":")[2])
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        if car:
            car_dict = {
                'brand': car.brand, 'model': car.model, 'year': car.year,
                'price': car.price, 'color': car.color, 'description': car.description,
                'images': car.images, 'transmission': car.transmission
            }
            await publish_admin_car(car_dict)
            await notify_matching_users(car.id)
            await callback.answer("🚀 Kanalga yuborildi!")
        else:
            await callback.answer("Topilmadi")

@router.callback_query(F.data == "admin:cars:list")
async def admin_back_to_list(callback: CallbackQuery):
    await callback.message.delete()
    await list_cars_admin(callback.message)


@router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message):
    """Show statistics"""
    if not await check_admin(message.from_user.id):
        return
    
    await message.answer(
        "📊 <b>STATISTIKA BO'LIMI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Quyidagi hisobotlardan birini tanlang:",
        reply_markup=statistics_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "stats:full")
async def generate_full_stats(callback: CallbackQuery):
    """Generate full statistics report"""
    await callback.answer("Hisobot tayyorlanmoqda... ⏳")
    
    analytics = SalesAnalytics()
    
    # Generate charts
    report = await analytics.generate_full_report()
    stats = await analytics.get_summary_stats()
    
    summary_text = (
        "📊 <b>TO'LIQ HISOBOT (30 kun)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 Jami sotuvlar: <b>{stats['total_sales']} ta</b>\n"
        f"💰 Jami foyda: <b>{stats['total_profit']:,.0f} $</b>\n"
        f"📊 O'rtacha foyda: <b>{stats['avg_profit']:,.0f} $</b>\n"
        f"🏆 Eng yaxshi kun: <b>{stats.get('best_day', 'N/A')}</b> ({stats.get('best_day_count', 0)} ta)"
    )
    
    await callback.message.answer(summary_text, parse_mode="HTML")
    
    # Send charts
    if report['daily_sales']:
        try:
            with open(report['daily_sales'], 'rb') as photo:
                await callback.message.answer_photo(photo, caption="📈 Kunlik sotuvlar dinamikasi")
        except Exception as e:
            logger.error(f"Error sending daily sales chart: {e}")
    
    if report['top_models']:
        try:
            with open(report['top_models'], 'rb') as photo:
                await callback.message.answer_photo(photo, caption="🏆 Top modellar")
        except Exception as e:
            logger.error(f"Error sending top models chart: {e}")


@router.message(F.text == "📥 Murojaatlar")
async def show_inquiries(message: Message):
    """Show pending inquiries"""
    if not await check_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        inquiries = await get_pending_inquiries(session)
    
    if not inquiries:
        await message.answer(
            "📥 <b>MUROJAATLAR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ Yangi murojaatlar yo'q!",
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        "📥 <b>YANGI MUROJAATLAR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    for inq in inquiries:
        inq_text = f"🆔 Ariza: <b>#{inq.id}</b>\n"
        inq_text += f"👤 Mijoz ID: <code>{inq.user_id}</code>\n"
        inq_text += f"📝 Turi: <b>{inq.inquiry_type.upper()}</b>\n"
        if inq.brand:
            inq_text += f"🚗 Moshina: <b>{inq.brand} {inq.model}</b>\n"
        if inq.price:
            inq_text += f"💰 Narx: <b>{inq.price:,.0f} $</b>\n"
        
        await message.answer(inq_text, reply_markup=inquiry_management_keyboard(inq.id), parse_mode="HTML")




@router.callback_query(F.data.startswith("inquiry:"))
async def inquiry_actions(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    inquiry_id = int(parts[2])
    
    async with async_session_maker() as session:
        if action == "accept":
            await update_inquiry_status(session, inquiry_id, "processing")
            await callback.answer("✅ Qabul qilindi")
            await callback.message.edit_text(callback.message.text + "\n\n👉 <b>HOLAT: JARAYONDA</b>", parse_mode="HTML")
        
        elif action == "reject":
            await update_inquiry_status(session, inquiry_id, "rejected")
            await callback.answer("❌ Rad etildi")
            await callback.message.edit_text(callback.message.text + "\n\n👉 <b>HOLAT: RAD ETILDI</b>", parse_mode="HTML")

        elif action == "call":
            await callback.answer("📞 Qo'ng'iroq (Placeholder)")

@router.callback_query(F.data.startswith("inquiry_complete:")) # Add this to keyboard or handle it
async def complete_inquiry_and_publish(callback: CallbackQuery):
    inquiry_id = int(callback.data.split(":")[1])
    async with async_session_maker() as session:
        from database.crud import get_inquiry_by_id, create_car
        inq = await get_inquiry_by_id(session, inquiry_id)
        if inq and inq.inquiry_type == "sell":
            # Convert to Car
            car = await create_car(
                session,
                brand=inq.brand,
                model=inq.model,
                year=inq.year,
                price=inq.price,
                description=inq.description,
                images=inq.images,
                is_available=True
            )
            await update_inquiry_status(session, inquiry_id, "completed")
            await callback.answer("✅ Sotuv muvaffaqiyatli yakunlandi va rasm katalogga qo'shildi!")
            await callback.message.edit_text(callback.message.text + f"\n\n🚀 <b>SOTILDI & KATALOGGA QO'SHILDI (ID: {car.id})</b>", parse_mode="HTML")
        else:
            await callback.answer("Xatolik yoki moshina emas")


# --- Missing Admin Handlers ---

@router.message(F.text == "💰 Sotuvni qayd qilish")
async def start_record_sale(message: Message, state: FSMContext):
    """Start recording a sale"""
    if not await check_admin(message.from_user.id): return
    await message.answer(
        "🚘 <b>SOTUV QAYD ETISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏷 <b>Sotilgan moshina brendini yozing:</b>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(RecordSaleStates.waiting_for_brand)

@router.message(RecordSaleStates.waiting_for_brand)
async def record_sale_brand(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ <b>Bekor qilindi</b>", reply_markup=admin_main_menu_keyboard(), parse_mode="HTML")
    await state.update_data(brand=message.text)
    await message.answer("🚙 <b>Model nomini yozing:</b>", parse_mode="HTML")
    await state.set_state(RecordSaleStates.waiting_for_model)

@router.message(RecordSaleStates.waiting_for_model)
async def record_sale_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("📅 <b>Yilini yozing:</b>", parse_mode="HTML")
    await state.set_state(RecordSaleStates.waiting_for_year)

@router.message(RecordSaleStates.waiting_for_year)
async def record_sale_year(message: Message, state: FSMContext):
    try:
        year = int(message.text)
    except (ValueError, TypeError):
        return await message.answer("❌ Yilni to'g'ri kiriting (masalan: 2022)")
    await state.update_data(year=year)
    await message.answer("💰 <b>Tan narxini kiriting (USD):</b>\n<i>Qanchaga olgan edingiz?</i>", parse_mode="HTML")
    await state.set_state(RecordSaleStates.waiting_for_purchase_price)

@router.message(RecordSaleStates.waiting_for_purchase_price)
async def record_sale_purchase_price(message: Message, state: FSMContext):
    try:
        purchase_price = float(message.text.replace(' ', '').replace(',', ''))
    except (ValueError, TypeError):
        return await message.answer("❌ Narxni to'g'ri kiriting (faqat raqam)")
    await state.update_data(purchase_price=purchase_price)
    await message.answer("💵 <b>Sotuv narxini kiriting (USD):</b>\n<i>Qanchaga sotdingiz?</i>", parse_mode="HTML")
    await state.set_state(RecordSaleStates.waiting_for_selling_price)

@router.message(RecordSaleStates.waiting_for_selling_price)
async def record_sale_selling_price(message: Message, state: FSMContext, bot: Bot):
    try:
        sell_price = float(message.text.replace(' ', '').replace(',', ''))
    except (ValueError, TypeError):
        return await message.answer("❌ Narxni to'g'ri kiriting (faqat raqam)")
    data = await state.get_data()
    profit = sell_price - data['purchase_price']
    
    async with async_session_maker() as session:
        await create_sold_car(
            session,
            brand=data['brand'],
            model=data['model'],
            year=data['year'],
            purchase_price=data['purchase_price'],
            selling_price=sell_price,
            profit=profit
        )
    
    await state.clear()
    
    profit_emoji = "🟢" if profit >= 0 else "🔴"
    
    await message.answer(
        f"✅ <b>SOTUV QAYD ETILDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚗 {data['brand']} {data['model']} ({data['year']})\n"
        f"💰 Olish: <b>{data['purchase_price']:,.0f} $</b>\n"
        f"💵 Sotish: <b>{sell_price:,.0f} $</b>\n\n"
        f"{profit_emoji} Foyda: <b>{profit:,.0f} $</b>",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML"
    )
@router.callback_query(F.data.startswith("scraped:"))
async def scraped_listing_actions(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    listing_id = int(callback.data.split(":")[2])
    
    if action == "add":
        await callback.answer("✅ Moshina bazaga qo'shildi (Simulyatsiya)")
    elif action == "skip":
        await callback.answer("❌ Inkor qilindi")
        await callback.message.delete()
    elif action == "send":
        await callback.answer("📤 Dadaga yuborildi")


@router.message(F.text == "📢 Xabar yuborish")
async def start_broadcast(message: Message, state: FSMContext):
    """Start broadcast"""
    if not await check_admin(message.from_user.id): return
    await message.answer(
        "📢 <b>XABAR YUBORISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Hamma foydalanuvchilarga yuboriladigan\n"
        "xabarni yozing.\n\n"
        "<i>Rasm ham yuborishingiz mumkin</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_msg(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ <b>Bekor qilindi</b>", reply_markup=admin_main_menu_keyboard(), parse_mode="HTML")
    
    from keyboards.admin_keyboards import broadcast_confirm_keyboard
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
    await message.answer(
        "❓ <b>Tasdiqlaysizmi?</b>\n\n"
        "⚠️ Xabar <b>hamma foydalanuvchilarga</b> yuboriladi!",
        reply_markup=broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.confirm_broadcast)

@router.callback_query(F.data == "broadcast:confirm", BroadcastStates.confirm_broadcast)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await callback.message.edit_text("🚀 <b>Xabar yuborilmoqda...</b>", parse_mode="HTML")
    
    from database.crud import get_all_users
    async with async_session_maker() as session:
        users = await get_all_users(session)
    
    count = 0
    for user in users:
        try:
            await bot.copy_message(user.telegram_id, data['chat_id'], data['msg_id'])
            count += 1
            await asyncio.sleep(0.1)  # Safe rate limit (Telegram max 30 msg/sec)
        except Exception:
            pass
    
    await state.clear()
    await callback.message.answer(
        f"✅ <b>Xabar {count} ta foydalanuvchiga yuborildi!</b>",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "broadcast:cancel", BroadcastStates.confirm_broadcast)
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ <b>Bekor qilindi</b>", parse_mode="HTML")


@router.message(F.text == "🖥️ Tizim Monitoringi")
async def show_system_monitoring(message: Message):
    """Show system health and monitoring stats"""
    try:
        from utils.currency import get_usd_rate
        from database.database import async_session_maker
        from sqlalchemy import select, func
        from database.models import User, Car, ScrapedListing
        import time
        import os
        from datetime import datetime, timedelta

        # Get currency rate
        usd_rate = await get_usd_rate()
        
        async with async_session_maker() as session:
            # DB Stats
            user_count = await session.scalar(select(func.count(User.id)))
            car_count = await session.scalar(select(func.count(Car.id)))
            scraped_count = await session.scalar(
                select(func.count(ScrapedListing.id))
                .where(ScrapedListing.scraped_at > datetime.utcnow() - timedelta(hours=24))
            )
            
            # Last scraped time
            last_scraped = await session.scalar(
                select(ScrapedListing.scraped_at)
                .order_by(ScrapedListing.scraped_at.desc())
                .limit(1)
            )
            last_scraped_str = last_scraped.strftime("%H:%M") if last_scraped else "Noma'lum"

        # System Load (approximate)
        try:
            load_avg = os.getloadavg()[0]  # 1 min load average
        except:
            load_avg = 0.0

        text = (
            "🖥️ <b>TIZIM MONITORINGI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💵 <b>Valyuta Kursi (CBU):</b>\n"
            f"🇺🇸 1 USD = <b>{usd_rate:,.0f} UZS</b>\n"
            "✅ Avtomatik yangilanadi\n\n"
            
            "🤖 <b>Scraper Holati:</b>\n"
            f"📥 So'nggi 24 soatda: <b>{scraped_count} ta</b> e'lon\n"
            f"⏱️ Oxirgi yangilanish: <b>{last_scraped_str}</b>\n\n"
            
            "🗄️ <b>Baza Statistikasi:</b>\n"
            f"👥 Foydalanuvchilar: <b>{user_count} ta</b>\n"
            f"🚗 Moshinalar: <b>{car_count} ta</b>\n\n"
            
            "⚙️ <b>Server Holati:</b>\n"
            f"🔥 Yuklama (Load): <b>{load_avg:.2f}</b>\n"
            f"🕒 Server vaqti: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        # Assuming 'logger' is defined elsewhere or will be added.
        # If not, this will cause a NameError.
        logger.error(f"Error showing system monitor: {e}")
        await message.answer("⚠️ Tizim ma'lumotlarini olishda xatolik bo'ldi.", parse_mode="HTML")


@router.callback_query(F.data.startswith("stats:"))
async def stats_callback_handler(callback: CallbackQuery):
    if callback.data == "stats:full": return # Handled already
    await callback.answer(f"Statistika ({callback.data.split(':')[1]}) tez orada tayyor bo'ladi!")
