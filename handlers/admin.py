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


@router.message(F.text == "📊 Admin Dashboard")
async def admin_dashboard(message: Message):
    """Admin dashboard with key statistics"""
    try:
        if not await check_admin(message.from_user.id):
            await message.answer("❌ Sizda ushbu buyruqqa ruxsat yo'q")
            return
        
        # Show loading
        loading_msg = await message.answer("🔄 Dashboard yuklanmoqda...")
        
        async with async_session_maker() as session:
            from database.crud import get_cars, get_pending_inquiries, get_user_buy_requests
            from database.models import User, BuyRequest
            
            # Get key statistics with error handling
            try:
                total_cars = len(await get_cars(session, limit=1000))
                pending_inquiries = len(await get_pending_inquiries(session))
                buy_requests = len(await get_user_buy_requests(session, 0))  # All requests
                
                # Get users count
                from sqlalchemy import select, func
                users_result = await session.execute(select(func.count(User.id)))
                total_users = users_result.scalar()
                
                # Get today's activity
                from datetime import datetime, timedelta
                today = datetime.utcnow().date()
                today_cars_result = await session.execute(
                    select(func.count(Car.id)).where(Car.created_at >= today)
                )
                today_cars = today_cars_result.scalar()
                
            except Exception as e:
                logger.error(f"Error fetching dashboard stats: {e}")
                total_cars = pending_inquiries = buy_requests = 0
                total_users = today_cars = 0
        
        # Delete loading message
        await loading_msg.delete()
        
        # Build dashboard keyboard
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📋 Moshinalar", callback_data="admin:cars"),
            InlineKeyboardButton(text="📞 Arizalar", callback_data="admin:inquiries")
        )
        builder.row(
            InlineKeyboardButton(text="🛒 Sotib olish arizalari", callback_data="admin:buy_requests"),
            InlineKeyboardButton(text="📈 Statistika", callback_data="admin:stats")
        )
        builder.row(
            InlineKeyboardButton(text="➕ Moshina qo'shish", callback_data="add_car:manual"),
            InlineKeyboardButton(text="📢 E'lon yuborish", callback_data="admin:broadcast")
        )
        builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu"))
        
        text = (
            f"📊 <b>ADMIN DASHBOARD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 <b>Foydalanuvchilar:</b> {total_users} ta\n"
            f"🚗 <b>Jami moshinalar:</b> {total_cars} ta\n"
            f"📞 <b>Kutilayotgan arizalar:</b> {pending_inquiries} ta\n"
            f"🛒 <b>Sotib olish arizalari:</b> {buy_requests} ta\n"
            f"📅 <b>Bugungi moshinalar:</b> {today_cars} ta\n\n"
            f"⚡ <b>Tezkor amallar:</b>"
        )
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        logger.info(f"Admin {message.from_user.id} viewed dashboard")
        
    except Exception as e:
        logger.error(f"Error in admin_dashboard: {e}")
        await message.answer(
            "❌ Dashboardni yuklashda xatolik yuz berdi.",
            reply_markup=admin_main_menu_keyboard()
        )


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
    """Process car price (Add or Edit)"""
    try:
        price = float(message.text.replace(" ", "").replace(",", ""))
        data = await state.get_data()
        
        # Check if EDIT mode
        if data.get('edit_car_id'):
            car_id = data['edit_car_id']
            async with async_session_maker() as session:
                await update_car(session, car_id, price=price)
            
            await message.answer(f"✅ Narx yangilandi: {price:,.0f} $")
            await state.clear()
            # Show edit menu again
            from keyboards.admin_keyboards import car_management_keyboard
            # We can't easily call callback handler from here, so just show menu
            # Or better, simulate callback to show edit menu? simplify: just show text
            await message.answer("Tahrirlash yakunlandi / Bosh menyuga qaytish", reply_markup=admin_main_menu_keyboard())
            return

        # Normal ADD flow
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
    """Process car mileage (Add or Edit)"""
    mileage = None
    if message.text != "/skip":
        try:
            mileage = int(message.text.replace(" ", "").replace(",", ""))
        except ValueError:
            await message.answer("❌ Iltimos, to'g'ri probeg kiriting")
            return
            
    data = await state.get_data()
    # Check if EDIT mode
    if data.get('edit_car_id'):
        car_id = data['edit_car_id']
        async with async_session_maker() as session:
            await update_car(session, car_id, mileage=mileage)
        
        await message.answer(f"✅ Probeg yangilandi: {mileage or 0:,} km")
        await state.clear()
        await message.answer("Tahrirlash yakunlandi", reply_markup=admin_main_menu_keyboard())
        return

    # Normal ADD flow
    await state.update_data(mileage=mileage)
    await message.answer(
        "🎨 <b>Rangini kiriting:</b>\n"
        "<i>Yoki /skip bosing</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_color)


@router.message(AddCarStates.waiting_for_color)
async def process_car_color(message: Message, state: FSMContext):
    """Process car color (Add or Edit)"""
    color = message.text
    if message.text == "/skip": color = None
    
    data = await state.get_data()
    # Check EDIT mode
    if data.get('edit_car_id'):
        car_id = data['edit_car_id']
        async with async_session_maker() as session:
            await update_car(session, car_id, color=color)
        
        await message.answer(f"✅ Rang yangilandi: {color or 'N/A'}")
        await state.clear()
        await message.answer("Tahrirlash yakunlandi", reply_markup=admin_main_menu_keyboard())
        return

    # Normal ADD flow
    await state.update_data(color=color)
    await message.answer(
        "📝 <b>Tavsifini kiriting:</b>\n"
        "<i>Yoki /skip bosing</i>",
        parse_mode="HTML"
    )
    await state.set_state(AddCarStates.waiting_for_description)


@router.message(AddCarStates.waiting_for_description)
async def process_car_description(message: Message, state: FSMContext):
    """Process car description (Add or Edit)"""
    desc = message.text
    if message.text == "/skip": desc = None

    data = await state.get_data()
    # Check EDIT mode
    if data.get('edit_car_id'):
        car_id = data['edit_car_id']
        async with async_session_maker() as session:
            await update_car(session, car_id, description=desc)
        
        await message.answer("✅ Tavsif yangilandi!")
        await state.clear()
        await message.answer("Tahrirlash yakunlandi", reply_markup=admin_main_menu_keyboard())
        return

    # Normal ADD flow
    await state.update_data(description=desc)
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

@router.callback_query(F.data.startswith("edit:photos:"))
async def edit_car_photos(callback: CallbackQuery, state: FSMContext):
    car_id = int(callback.data.split(":")[2])
    await state.update_data(edit_car_id=car_id, edit_field="photos", photos_list=[])
    await state.set_state(AddCarStates.waiting_for_images)
    await callback.message.answer(
        "📸 <b>Yangi rasmlarni yuboring</b>\n"
        "Eski rasmlar o'rniga shu yangilari qo'yiladi.\n"
        "Birinchi rasm asosiy bo'ladi.\n"
        "Tugatgach <b>✅ Tayyor!</b> bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Tayyor!")]],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AddCarStates.waiting_for_images, (F.text == "/done") | (F.text == "✅ Tayyor!") | (F.text == "/skip"))
async def process_car_images_done(message: Message, state: FSMContext):
    """Finish image collection (Add or Edit)"""
    data = await state.get_data()
    photos = data.get('photos_list', [])
    
    images_data = None
    if photos:
        images_data = {
            'main': photos[0],
            'gallery': photos[1:] if len(photos) > 1 else []
        }
    elif message.text == "/skip":
        images_data = None
    else:
        await message.answer("Hech bo'lmasa bitta rasm yuboring yoki /skip bosing.")
        return

    # Check EDIT mode
    if data.get('edit_car_id'):
        car_id = data['edit_car_id']
        # If user skipped, maybe we don't want to wipe existing photos?
        # Assuming if skipped in edit mode -> no change.
        if images_data:
            async with async_session_maker() as session:
                await update_car(session, car_id, images=images_data)
            await message.answer("✅ Rasmlar yangilandi!")
        else:
            await message.answer("Rasmlar o'zgarishsiz qoldirildi.")
            
        await state.clear()
        await message.answer("Tahrirlash yakunlandi", reply_markup=admin_main_menu_keyboard())
        return

    # Normal ADD flow
    if images_data:
        await state.update_data(images=images_data)
    else:
        await state.update_data(images=None)

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


@router.callback_query(F.data.startswith("car_action:"))
async def car_quick_action(callback: CallbackQuery):
    """Quick actions for cars (approve/reject)"""
    parts = callback.data.split(":")
    action = parts[1]
    car_id = int(parts[2])
    
    if not await check_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        if not car:
            await callback.answer("❌ Moshina topilmadi", show_alert=True)
            return
        
        if action == "approve":
            # Mark as available/published
            await update_car(session, car_id, is_available=True)
            await callback.answer(f"✅ {car.brand} {car.model} tasdiqlandi", show_alert=True)
            
        elif action == "reject":
            # Mark as unavailable
            await update_car(session, car_id, is_available=False)
            await callback.answer(f"❌ {car.brand} {car.model} rad etildi", show_alert=True)
            
        elif action == "feature":
            # Mark as featured
            await update_car(session, car_id, is_featured=True)
            await callback.answer(f"⭐ {car.brand} {car.model} asosiyga qo'shildi", show_alert=True)


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback_handler(callback: CallbackQuery):
    """Admin dashboard callbacks"""
    action = callback.data.split(":")[1]
    
    if action == "cars":
        await list_cars_admin(callback.message)
    elif action == "inquiries":
        # Show pending inquiries
        async with async_session_maker() as session:
            inquiries = await get_pending_inquiries(session)
        
        if not inquiries:
            await callback.answer("📞 Kutilayotgan arizalar yo'q", show_alert=True)
            return
        
        text = f"📞 <b>KUTILAYOTGAN ARIZALAR ({len(inquiries)} ta)</b>\n\n"
        for i, inquiry in enumerate(inquiries[:5], 1):
            text += f"{i}. {inquiry.brand} {inquiry.model} - {inquiry.price:,.0f} $\n"
        
        await callback.message.answer(text, parse_mode="HTML")
        
    elif action == "buy_requests":
        # Show buy requests
        async with async_session_maker() as session:
            from database.crud import get_user_buy_requests
            requests = await get_user_buy_requests(session, 0)  # All requests
        
        if not requests:
            await callback.answer("🛒 Sotib olish arizalari yo'q", show_alert=True)
            return
        
        text = f"🛒 <b>SOTIB OLISH ARIZALARI ({len(requests)} ta)</b>\n\n"
        for i, req in enumerate(requests[:5], 1):
            text += f"{i}. {req.brand} {req.model} - {req.budget_min:,.0f}-${req.budget_max:,.0f}\n"
        
        await callback.message.answer(text, parse_mode="HTML")
        
    elif action == "stats":
        await show_advanced_analytics(callback.message)
    
    await callback.answer()


async def show_advanced_analytics(message: Message):
    """Show advanced analytics dashboard"""
    try:
        # Show loading
        loading_msg = await message.answer("📊 Analiz yuklanmoqda...")
        
        async with async_session_maker() as session:
            from database.crud import get_cars, get_pending_inquiries, get_user_buy_requests
            from database.models import User, BuyRequest, Car
            from sqlalchemy import select, func, and_, or_
            from datetime import datetime, timedelta
            
            # Basic stats
            total_cars = len(await get_cars(session, limit=1000))
            pending_inquiries = len(await get_pending_inquiries(session))
            buy_requests = len(await get_user_buy_requests(session, 0))
            
            # User stats
            users_result = await session.execute(select(func.count(User.id)))
            total_users = users_result.scalar()
            
            # Today's stats
            today = datetime.utcnow().date()
            today_cars_result = await session.execute(
                select(func.count(Car.id)).where(Car.created_at >= today)
            )
            today_cars = today_cars_result.scalar()
            
            # This week stats
            week_ago = today - timedelta(days=7)
            week_cars_result = await session.execute(
                select(func.count(Car.id)).where(Car.created_at >= week_ago)
            )
            week_cars = week_cars_result.scalar()
            
            # Price distribution
            price_ranges = [
                ("0-5k", 0, 5000),
                ("5k-10k", 5000, 10000),
                ("10k-15k", 10000, 15000),
                ("15k-20k", 15000, 20000),
                ("20k+", 20000, 1000000)
            ]
            
            price_dist_text = "💰 <b>NARX TARQALISHI</b>\n"
            for label, min_price, max_price in price_ranges:
                count_result = await session.execute(
                    select(func.count(Car.id)).where(
                        and_(Car.price >= min_price, Car.price < max_price)
                    )
                )
                count = count_result.scalar()
                percentage = (count / total_cars * 100) if total_cars > 0 else 0
                price_dist_text += f"{label}: {count} ta ({percentage:.1f}%)\n"
            
            # Brand distribution
            brand_result = await session.execute(
                select(Car.brand, func.count(Car.id))
                .group_by(Car.brand)
                .order_by(func.count(Car.id).desc())
                .limit(5)
            )
            top_brands = brand_result.fetchall()
            
            brand_dist_text = "\n🏷 <b>TOP 5 BRENDLAR</b>\n"
            for brand, count in top_brands:
                percentage = (count / total_cars * 100) if total_cars > 0 else 0
                brand_dist_text += f"{brand}: {count} ta ({percentage:.1f}%)\n"
            
            # Year distribution
            year_result = await session.execute(
                select(Car.year, func.count(Car.id))
                .group_by(Car.year)
                .order_by(func.count(Car.id).desc())
                .limit(5)
            )
            top_years = year_result.fetchall()
            
            year_dist_text = "\n📅 <b>TOP 5 YILLAR</b>\n"
            for year, count in top_years:
                percentage = (count / total_cars * 100) if total_cars > 0 else 0
                year_dist_text += f"{year}: {count} ta ({percentage:.1f}%)\n"
            
            # Activity trends
            last_7_days = []
            for i in range(7):
                date = today - timedelta(days=i)
                day_result = await session.execute(
                    select(func.count(Car.id)).where(
                        func.date(Car.created_at) == date
                    )
                )
                count = day_result.scalar()
                last_7_days.append((date.strftime("%d-%m"), count))
            
            trends_text = "\n📈 <b>7 KUNLIK TRENDS</b>\n"
            for date, count in reversed(last_7_days):
                trends_text += f"{date}: {count} ta\n"
        
        await loading_msg.delete()
        
        # Build comprehensive analytics report
        text = "📊 <b>ADVANCED ANALYTICS DASHBOARD</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Overview
        text += "📋 <b>UMUMIY KO'RSATGICHLAR</b>\n"
        text += f"👥 Foydalanuvchilar: {total_users} ta\n"
        text += f"🚗 Jami moshinalar: {total_cars} ta\n"
        text += f"📞 Kutilayotgan arizalar: {pending_inquiries} ta\n"
        text += f"🛒 Sotib olish arizalari: {buy_requests} ta\n"
        text += f"📅 Bugungi moshinalar: {today_cars} ta\n"
        text += f"📊 Haftalik moshinalar: {week_cars} ta\n\n"
        
        text += price_dist_text
        text += brand_dist_text
        text += year_dist_text
        text += trends_text
        
        text += "\n⚠️ Ma'lumotlar real vaqtda yangilanadi"
        
        # Action buttons
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📥 Excel yuklash", callback_data="analytics:export"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:stats")
        )
        builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:dashboard"))
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        logger.info(f"Advanced analytics viewed by admin {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in show_advanced_analytics: {e}")
        await message.answer(
            "❌ Analiz ma'lumotlarini yuklashda xatolik yuz berdi.",
            reply_markup=admin_main_menu_keyboard()
        )


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
    
    for i, car in enumerate(cars[:5], 1):  # Show first 5 with quick actions
        status = "✅" if car.is_available else "❌"
        featured = "⭐" if getattr(car, 'is_featured', False) else ""
        car_text = f"{status} {featured} {i}. {car.brand} {car.model} - {car.price:,.0f} $\n"
        car_text += f"   📅 {car.year} | 🛣 {car.mileage or 0:,} km\n"
        
        # Quick action buttons
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"car_action:approve:{car.id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"car_action:reject:{car.id}")
        )
        builder.row(
            InlineKeyboardButton(text="⭐ Asosiy qilish", callback_data=f"car_action:feature:{car.id}"),
            InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_car:{car.id}")
        )
        
        await message.answer(car_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    
    if len(cars) > 5:
        await message.answer(f"...va yana {len(cars) - 5} ta mashina", parse_mode="HTML")

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
        [
            InlineKeyboardButton(text="📸 Rasmlarni o'zgartirish", callback_data=f"edit:photos:{car_id}"),
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
    """Ask for confirmation before deleting car"""
    car_id = int(callback.data.split(":")[3])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"admin:car:del_confirm:{car_id}")],
        [InlineKeyboardButton(text="❌ Yo'q, qaytish", callback_data=f"admin:car:edit:{car_id}")]
    ])
    
    await callback.message.edit_text(
        f"🗑 <b>Moshina #{car_id} ni o'chirmoqchimisiz?</b>\n\n"
        "Bu amalni ortga qaytarib bo'lmaydi.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:car:del_confirm:"))
async def admin_delete_car_confirm(callback: CallbackQuery):
    """Actually delete or archive the car"""
    car_id = int(callback.data.split(":")[3])
    
    async with async_session_maker() as session:
        # Check if car exists
        car = await get_car_by_id(session, car_id)
        if car:
            # We mark as unavailable (soft delete) or actually delete?
            # User request: "Delete". Usually soft delete is safer.
            # Let's do soft delete (is_available=False) + maybe a note
            car.is_available = False
            car.is_featured = False
            # car.pipeline_status = 'deleted' # if we had this
            
            await session.commit()
            await callback.answer("✅ Moshina o'chirildi (arxivlandi)")
            
            # Go back to list
            await list_cars_admin(callback.message)
            await callback.message.delete()
        else:
            await callback.answer("Xatolik: topilmadi", show_alert=True)
            await list_cars_admin(callback.message)

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


@router.callback_query(F.data.startswith("admin:car:status:"))
async def admin_change_status_menu(callback: CallbackQuery):
    """Show status change options"""
    car_id = int(callback.data.split(":")[3])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Sotuvda (Available)", callback_data=f"status:set:{car_id}:available")],
        [InlineKeyboardButton(text="🤝 Band qilingan (Reserved)", callback_data=f"status:set:{car_id}:reserved")],
        [InlineKeyboardButton(text="🔴 Sotildi (Sold)", callback_data=f"status:set:{car_id}:sold")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data=f"admin:cars:list")]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("status:set:"))
async def admin_set_status(callback: CallbackQuery):
    """Set new status for car"""
    parts = callback.data.split(":")
    car_id = int(parts[2])
    new_status = parts[3]
    
    async with async_session_maker() as session:
        car = await get_car_by_id(session, car_id)
        if car:
            # Simple mapping to is_available for now
            # If you add 'status' column later, update it here
            if new_status == "available":
                car.is_available = True
                status_text = "✅ Sotuvda"
            elif new_status == "sold":
                car.is_available = False
                status_text = "🔴 Sotildi"
            else:
                car.is_available = False # Reserved treated as unavailable logic-wise
                status_text = "🤝 Band qilingan"
            
            # If you added 'status' column to Car model:
            # car.status = new_status
            
            await session.commit()
            await callback.answer(f"Status o'zgardi: {status_text}")
            
            # Return to list
            await list_cars_admin(callback.message)
            await callback.message.delete()
        else:
            await callback.answer("Xatolik: Moshina topilmadi")


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
    
    # 1. Gather all data
    stats = await analytics.get_summary_stats()
    cust_stats = await analytics.get_customer_stats()
    pop_cars = await analytics.get_popular_cars()
    price_stats = await analytics.get_price_analysis()
    
    # Generate charts
    report = await analytics.generate_full_report()
    
    # 2. Format the text
    summary_text = (
        "📊 <b>TO'LIQ HISOBOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📈 <b>Savdo statistikasi (30 kun)</b>\n"
        f"├─ Sotilganlar: <b>{stats.get('total_sales', 0)} ta</b>\n"
        f"├─ Jami foyda: <b>{stats.get('total_profit', 0):,.0f} $</b>\n"
        f"├─ O'rtacha foyda: <b>{stats.get('avg_profit', 0):,.0f} $</b>\n"
        f"└─ Eng yaxshi kun: {stats.get('best_day', 'N/A')} ({stats.get('best_day_count', 0)} ta)\n\n"
        
        "👥 <b>Mijozlar</b>\n"
        f"├─ Jami: <b>{cust_stats.get('total', 0)} ta</b>\n"
        f"├─ Faol (7 kun): <b>{cust_stats.get('active', 0)} ta</b>\n"
        f"└─ Yangi (7 kun): <b>{cust_stats.get('new', 0)} ta</b>\n\n"
        
        "🔥 <b>Eng mashhur mashinalar (Top 3)</b>\n"
    )
    
    i = 1
    for car in pop_cars:
        summary_text += f"├─ {i}. {car['brand']} {car['model']} ({car['views']} ko'rildi)\n"
        i += 1
    if not pop_cars:
        summary_text += "└─ Ma'lumot yo'q\n"
    
    summary_text += (
        "\n💰 <b>Narx tahlili (Sotuvdagi)</b>\n"
        f"├─ O'rtacha narx: <b>{price_stats.get('avg_price', 0):,.0f} $</b>\n"
        f"├─ Eng qimmat: <b>{price_stats.get('max_price', 0):,.0f} $</b>\n"
        f"└─ Eng arzon: <b>{price_stats.get('min_price', 0):,.0f} $</b>\n"
    )
    
    await callback.message.answer(summary_text, parse_mode="HTML")
    
    # 3. Send charts
    if report.get('daily_sales'):
        try:
            from aiogram.types import FSInputFile
            photo = FSInputFile(report['daily_sales'])
            await callback.message.answer_photo(photo, caption="📈 Kunlik sotuvlar dinamikasi")
        except Exception as e:
            logger.error(f"Error sending daily sales chart: {e}")
    
    if report.get('top_models'):
        try:
            from aiogram.types import FSInputFile
            photo = FSInputFile(report['top_models'])
            await callback.message.answer_photo(photo, caption="🏆 Top modellar")
        except Exception as e:
            logger.error(f"Error sending top models chart: {e}")
            
    # 4. Excel report button?
    # For now just text



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
