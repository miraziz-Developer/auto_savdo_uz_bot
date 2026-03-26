# 🚗 AvtoSavdo Bot - Tizim Qanday Ishlaydi

## 📖 Mundarija
1. [Umumiy Tasavvur](#umumiy-tasavvur)
2. [Mijoz Yo'li (User Journey)](#mijoz-yoli)
3. [Admin Yo'li (Admin Journey)](#admin-yoli)
4. [Backend Jarayonlar](#backend-jarayonlar)
5. [Database Tuzilishi](#database-tuzilishi)
6. [Real Misollar](#real-misollar)

---

## 🎯 Umumiy Tasavvur

### Tizim 3 Qismdan Iborat:

```
┌─────────────────────────────────────────────────────────┐
│                    AVTOSAVDO TIZIMI                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1️⃣ MIJOZ INTERFEYSI (Telegram Bot)                   │
│     └─ Katalog, Qidiruv, Obuna, Sevimlilar            │
│                                                         │
│  2️⃣ ADMIN INTERFEYSI (Telegram Bot)                   │
│     └─ Moshina qo'shish, CRM, Statistika              │
│                                                         │
│  3️⃣ BACKEND TIZIMI (Avtomatik)                        │
│     └─ Web Scraping, Xabarnomalar, Analytics           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 👤 Mijoz Yo'li (User Journey)

### BOSQICH 1️⃣: Ro'yxatdan O'tish

```
┌──────────────────────────────────────────────────┐
│  1. Mijoz botga /start yuboradi                 │
│     ↓                                            │
│  2. Bot xush kelibsiz xabarini yuboradi         │
│     ↓                                            │
│  3. Database'da User yaratiladi                  │
│     ↓                                            │
│  4. Asosiy menyu ko'rsatiladi                   │
└──────────────────────────────────────────────────┘

💾 DATABASE:
users jadvalidagi yangi qator:
┌────────────┬──────────┬─────────────────────┐
│ telegram_id│ username │ full_name           │
├────────────┼──────────┼─────────────────────┤
│ 123456789  │ @alisher │ Alisher Rahmonov    │
└────────────┴──────────┴─────────────────────┘
```

**Kod (handlers/common.py):**
```python
@router.message(CommandStart())
async def cmd_start(message: Message):
    # 1. Foydalanuvchini database'ga saqlash
    user = await get_or_create_user(
        session, 
        telegram_id=message.from_user.id
    )
    
    # 2. Asosiy menyuni ko'rsatish
    await message.answer(
        "Xush kelibsiz!",
        reply_markup=main_menu_keyboard()
    )
```

---

### BOSQICH 2️⃣: Moshina Qidirish

```
VARIANT A: KATALOG ORQALI
┌──────────────────────────────────────────────────┐
│  1. Mijoz "🚗 Katalog" tugmasini bosadi          │
│     ↓                                            │
│  2. Bot database'dan moshinalarni oladi         │
│     ↓                                            │
│  3. Birinchi moshinani ko'rsatadi               │
│     ↓                                            │
│  4. Mijoz moshina haqida ma'lumot oladi         │
└──────────────────────────────────────────────────┘

VARIANT B: FILTRLAR BILAN
┌──────────────────────────────────────────────────┐
│  1. Mijoz "🔍 Qidiruv" tugmasini bosadi          │
│     ↓                                            │
│  2. Filtrlarni ko'rsatadi                       │
│     ↓                                            │
│  3. Mijoz filtrlarni to'ldiradi:                │
│     • Brend: Chevrolet                          │
│     • Model: Gentra                             │
│     • Yil: 2020+                                │
│     • Narx: 150,000,000 gacha                   │
│     ↓                                            │
│  4. Bot filtrga mos moshinalarni topadi         │
│     ↓                                            │
│  5. Natijalarni ko'rsatadi                      │
└──────────────────────────────────────────────────┘
```

**SQL Query (database/crud.py):**
```python
async def get_cars(session, brand="Chevrolet", year_from=2020, price_to=150000000):
    query = select(Car).where(
        Car.brand.ilike("%Chevrolet%"),
        Car.year >= 2020,
        Car.price <= 150000000
    )
    result = await session.execute(query)
    return result.scalars().all()
```

---

### BOSQICH 3️⃣: Moshinani Ko'rish

```
┌──────────────────────────────────────────────────┐
│  MOSHINA SAHIFASI                                │
├──────────────────────────────────────────────────┤
│                                                  │
│  🚗 Chevrolet Gentra                            │
│  📅 Yil: 2022                                   │
│  💰 Narx: 120,000,000 so'm                      │
│  🎨 Rang: Oq                                    │
│  ⚙️ Korobka: Avtomat                            │
│  ⛽ Yoqilg'i: Benzin                            │
│  📏 Probeg: 25,000 km                           │
│                                                  │
│  ⭐ Reyting: 4.5/5.0 (12 sharh)                │
│  👁 Ko'rishlar: 156                             │
│                                                  │
│  📝 Ekspert xulosasi:                           │
│  "A'lo holatda, original kraska..."             │
│                                                  │
│  ┌─────────────┬─────────────┐                 │
│  │ 📞 Bog'lanish│ ❤️ Sevimlilar│                 │
│  ├─────────────┼─────────────┤                 │
│  │ ⭐ Sharh     │ 🖼 Rasmlar  │                 │
│  ├─────────────┴─────────────┤                 │
│  │      📤 Ulashish           │                 │
│  └────────────────────────────┘                 │
└──────────────────────────────────────────────────┘
```

**Kod (handlers/catalog.py):**
```python
async def show_car_detail(message, car_id):
    # 1. Moshinani database'dan olish
    car = await get_car_by_id(session, car_id)
    
    # 2. Ko'rishlar sonini oshirish
    await increment_car_views(session, car_id)
    
    # 3. Reyting va sharhlarni olish
    rating = await get_car_average_rating(session, car_id)
    review_count = await get_car_review_count(session, car_id)
    
    # 4. Ma'lumotlarni formatlash va yuborish
    await message.answer_photo(
        photo=car.images['main'],
        caption=formatted_text,
        reply_markup=car_detail_keyboard(car_id)
    )
```

---

### BOSQICH 4️⃣: Sevimlilar

```
QOSHISH:
┌──────────────────────────────────────────────────┐
│  1. Mijoz ❤️ tugmasini bosadi                    │
│     ↓                                            │
│  2. Bot favorites jadvaliga qo'shadi            │
│     ↓                                            │
│  3. "❤️ Sevimlilarga qo'shildi!" xabari         │
└──────────────────────────────────────────────────┘

💾 DATABASE (favorites jadvali):
┌────────────┬────────┬─────────────┐
│ user_id    │ car_id │ created_at  │
├────────────┼────────┼─────────────┤
│ 123456789  │ 42     │ 2026-02-10  │
└────────────┴────────┴─────────────┘

KORISH:
┌──────────────────────────────────────────────────┐
│  1. Mijoz "❤️ Sevimlilar" tugmasini bosadi      │
│     ↓                                            │
│  2. Bot user_id bo'yicha sevimlilarni oladi    │
│     ↓                                            │
│  3. Ro'yxatni ko'rsatadi                        │
└──────────────────────────────────────────────────┘
```

**Kod (handlers/favorites.py):**
```python
@router.callback_query(F.data.startswith("car:favorite:"))
async def toggle_favorite(callback):
    car_id = int(callback.data.split(":")[2])
    
    # Sevimlilarga qo'shish
    added = await add_to_favorites(session, user_id, car_id)
    
    if added:
        await callback.answer("❤️ Sevimlilarga qo'shildi!")
```

---

### BOSQICH 5️⃣: Sharh Yozish

```
┌──────────────────────────────────────────────────┐
│  1. Mijoz "⭐ Sharh yozish" tugmasini bosadi     │
│     ↓                                            │
│  2. Bot yulduzlar klaviaturasini ko'rsatadi     │
│     ⭐  ⭐⭐  ⭐⭐⭐  ⭐⭐⭐⭐  ⭐⭐⭐⭐⭐        │
│     ↓                                            │
│  3. Mijoz 5 yulduz tanlaydi                     │
│     ↓                                            │
│  4. Bot izoh so'raydi                           │
│     ↓                                            │
│  5. Mijoz: "Juda yaxshi moshina!"               │
│     ↓                                            │
│  6. Bot database'ga saqlaydi                    │
│     ↓                                            │
│  7. "✅ Rahmat! Sizning bahongiz saqlandi"      │
└──────────────────────────────────────────────────┘

💾 DATABASE (reviews jadvali):
┌────────────┬────────┬────────┬─────────────────────┐
│ user_id    │ car_id │ rating │ comment             │
├────────────┼────────┼────────┼─────────────────────┤
│ 123456789  │ 42     │ 5      │ Juda yaxshi moshina!│
└────────────┴────────┴────────┴─────────────────────┘
```

**Kod (handlers/reviews.py):**
```python
@router.callback_query(F.data.startswith("rating:"))
async def process_rating(callback, state):
    rating = int(callback.data.split(":")[1])  # 5
    await state.update_data(rating=rating)
    await callback.message.edit_text("Izohni yozing:")

@router.message(ReviewStates.waiting_for_comment)
async def process_comment(message, state):
    data = await state.get_data()
    
    # Database'ga saqlash
    await create_review(
        session,
        user_id=message.from_user.id,
        car_id=data['car_id'],
        rating=data['rating'],
        comment=message.text
    )
```

---

### BOSQICH 6️⃣: Obuna (Subscription)

```
OBUNA YARATISH:
┌──────────────────────────────────────────────────┐
│  1. Mijoz "🔔 Obuna" tugmasini bosadi            │
│     ↓                                            │
│  2. Bot qidiruv parametrlarini so'raydi         │
│     ↓                                            │
│  3. Mijoz to'ldiradi:                           │
│     • Brend: Chevrolet                          │
│     • Model: Malibu                             │
│     • Yil: 2020+                                │
│     • Narx: 200,000,000 gacha                   │
│     ↓                                            │
│  4. Bot subscription'ni saqlaydi                │
│     ↓                                            │
│  5. "✅ Obuna yaratildi! Yangi moshina          │
│      chiqqanda xabar beramiz"                   │
└──────────────────────────────────────────────────┘

💾 DATABASE (subscriptions jadvali):
┌────────────┬──────────┬────────┬──────────┬──────────┐
│ user_id    │ brand    │ model  │ year_from│ price_to │
├────────────┼──────────┼────────┼──────────┼──────────┤
│ 123456789  │Chevrolet │ Malibu │ 2020     │200000000 │
└────────────┴──────────┴────────┴──────────┴──────────┘

XABARNOMA (Avtomatik):
┌──────────────────────────────────────────────────┐
│  BACKEND TIZIMI:                                 │
│  1. Admin yangi moshina qo'shdi:                │
│     Chevrolet Malibu 2021, 180,000,000          │
│     ↓                                            │
│  2. Backend obunalarni tekshiradi               │
│     ↓                                            │
│  3. Mos obunani topadi (user 123456789)         │
│     ↓                                            │
│  4. Mijozga xabar yuboradi:                     │
│     🔔 "Sizning qidiruvingizga mos moshina      │
│          topildi!"                               │
└──────────────────────────────────────────────────┘
```

**Kod (database/crud.py):**
```python
async def find_matching_subscriptions(session, car):
    """Moshinaga mos obunalarni topish"""
    query = select(Subscription).where(
        Subscription.brand.ilike(f"%{car.brand}%"),
        Subscription.year_from <= car.year,
        Subscription.price_to >= car.price
    )
    
    result = await session.execute(query)
    return result.scalars().all()
```

---

### BOSQICH 7️⃣: Bog'lanish

```
┌──────────────────────────────────────────────────┐
│  1. Mijoz "📞 Bog'lanish" tugmasini bosadi       │
│     ↓                                            │
│  2. Bot admin kontaktlarini ko'rsatadi:         │
│     📞 Telefon: +998 90 123 45 67               │
│     📱 Telegram: @Real_Avto_Admin               │
│     ⏰ Ish vaqti: 9:00-20:00                    │
│     ↓                                            │
│  3. Mijoz telefon qiladi yoki yozadi           │
│     ↓                                            │
│  4. Admin javob beradi va ko'rib-savdo qiladi  │
└──────────────────────────────────────────────────┘

❌ TOLOV TIZIMI YO'Q!
✅ Faqat ko'rib-savdo va kelishuv
```

---

## 👨‍💼 Admin Yo'li (Admin Journey)

### ADMIN BOSQICH 1️⃣: Moshina Qo'shish

```
┌──────────────────────────────────────────────────┐
│  1. Admin "➕ Moshina qo'shish" bosadi           │
│     ↓                                            │
│  2. Bot FSM (Form State Machine) boshlaydi      │
│     ↓                                            │
│  3. Bot ketma-ket so'raydi:                     │
│     • Brend? → Chevrolet                        │
│     • Model? → Gentra                           │
│     • Yil? → 2022                               │
│     • Narx? → 120000000                         │
│     • Probeg? → 25000                           │
│     • Rang? → Oq                                │
│     • Tavsif? → A'lo holatda                    │
│     • Rasm? → [PHOTO]                           │
│     ↓                                            │
│  4. Tasdiqlash:                                  │
│     ✅ Ma'lumotlarni ko'rsatadi                 │
│     "Saqlashni tasdiqlaysizmi?"                 │
│     ↓                                            │
│  5. Admin "✅ Ha" bosadi                        │
│     ↓                                            │
│  6. Database'ga saqlanadi                       │
│     ↓                                            │
│  7. Obunalarni tekshiradi                       │
│     ↓                                            │
│  8. Mos obunalar topilsa xabar yuboradi        │
└──────────────────────────────────────────────────┘
```

**Kod (handlers/admin.py):**
```python
# STEP 1: Brend so'rash
@router.message(F.text == "➕ Moshina qo'shish")
async def start_add_car(message, state):
    await message.answer("Brend?")
    await state.set_state(AddCarStates.waiting_for_brand)

# STEP 2: Brend saqlash, model so'rash
@router.message(AddCarStates.waiting_for_brand)
async def process_brand(message, state):
    await state.update_data(brand=message.text)
    await message.answer("Model?")
    await state.set_state(AddCarStates.waiting_for_model)

# ... va hokazo barcha ma'lumotlar uchun

# OXIRGI STEP: Tasdiqlash
@router.callback_query(F.data == "confirm:add_car")
async def confirm_add_car(callback, state):
    data = await state.get_data()
    
    # Database'ga saqlash
    car = await create_car(session, **data)
    
    # Obunalarni tekshirish
    subscriptions = await find_matching_subscriptions(session, car)
    
    # Xabarnomalar yuborish
    for sub in subscriptions:
        await notify_subscriber(sub.user_id, car)
```

---

### ADMIN BOSQICH 2️⃣: CRM Dashboard

```
┌──────────────────────────────────────────────────┐
│  📊 CRM DASHBOARD                                │
├──────────────────────────────────────────────────┤
│                                                  │
│  [👥 Mijozlar] [📊 Statistika]                  │
│  [📥 Murojaatlar] [🔔 Obunalar]                 │
│  [🚗 Mashhur moshinalar] [📈 Faollik]           │
│                                                  │
└──────────────────────────────────────────────────┘

1️⃣ MIJOZLAR BO'LIMI:
┌──────────────────────────────────────────────────┐
│  👥 Mijozlar Statistikasi                       │
│                                                  │
│  📊 Jami foydalanuvchilar: 1,234                │
│  ✅ Faol (7 kun): 456                           │
│  🆕 Yangi (30 kun): 123                         │
│  📱 Telefon bergan: 789                         │
│                                                  │
│  📈 Konversiya: 64.0%                           │
└──────────────────────────────────────────────────┘

2️⃣ STATISTIKA:
┌──────────────────────────────────────────────────┐
│  📊 Umumiy Statistika                           │
│                                                  │
│  🚗 Jami moshinalar: 89                         │
│  ✅ Mavjud: 67                                  │
│  📥 Kutilayotgan murojaatlar: 12                │
│  🔔 Faol obunalar: 234                          │
│                                                  │
│  🏆 Eng ko'p ko'rilgan:                         │
│  Chevrolet Gentra (156 marta)                   │
└──────────────────────────────────────────────────┘
```

**Kod (handlers/crm.py):**
```python
@router.callback_query(F.data == "crm:customers")
async def show_customers(callback):
    # Jami userlar
    total_users = await session.execute(
        select(func.count(User.id))
    )
    
    # Faol userlar (7 kun)
    week_ago = datetime.now() - timedelta(days=7)
    active_users = await session.execute(
        select(func.count(User.id))
        .where(User.last_activity >= week_ago)
    )
    
    # Statistikani formatlash va yuborish
    text = f"""
👥 Mijozlar Statistikasi

📊 Jami: {total_users.scalar()}
✅ Faol: {active_users.scalar()}
...
    """
    await callback.message.edit_text(text)
```

---

## 🤖 Backend Jarayonlar (Avtomatik)

### JARAYON 1️⃣: Web Scraping (OLX va Avtoelon)

```
┌────────────────────────────────────────────────────────┐
│  CELERY BEAT SCHEDULER                                 │
│  (Har 5 minutda avtomatik ishga tushadi)              │
└────────────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────────────┐
│  SCRAPING BOSQICHI:                                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. Playwright brauzerni ochadi                       │
│     ↓                                                  │
│  2. OLX.uz ga kiradi                                  │
│     URL: olx.uz/transport/legkovye-avtomobili/        │
│     ↓                                                  │
│  3. Sahifani parse qiladi (HTML)                      │
│     ↓                                                  │
│  4. Har bir e'lonni oladi:                            │
│     • Sarlavha                                         │
│     • Narx                                             │
│     • Yil                                              │
│     • Rasm URL                                         │
│     • E'lon URL                                        │
│     ↓                                                  │
│  5. Avtoelon.uz uchun qaytaradi                       │
│     ↓                                                  │
│  6. Database'da mavjudligini tekshiradi               │
│     ↓                                                  │
│  7. Yangi e'lonlarni saqlaydi                         │
└────────────────────────────────────────────────────────┘
```

**Kod (scrapers/olx_scraper.py):**
```python
async def scrape_listings(self, max_pages=3):
    # 1. Brauzerni ochish
    await self.init_browser()
    
    listings = []
    for page_num in range(1, max_pages + 1):
        url = f"https://www.olx.uz/transport/legkovye-avtomobili/?page={page_num}"
        
        # 2. Sahifaga kirish
        await self.page.goto(url)
        
        # 3. E'lonlarni topish
        elements = await self.page.query_selector_all('[data-cy="l-card"]')
        
        # 4. Har birini parse qilish
        for element in elements:
            listing = await self.parse_listing(element)
            listings.append(listing)
    
    return listings
```

---

### JARAYON 2️⃣: Yangi E'lonlarni Qayta Ishlash

```
┌────────────────────────────────────────────────────────┐
│  LISTINGLARNI QAYTA ISHLASH:                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. Qayta ishlanmagan e'lonlarni oladi                │
│     ↓                                                  │
│  2. Har bir listing uchun:                            │
│     ↓                                                  │
│     a) Narxni bozor narxi bilan solishtiradi         │
│        ↓                                               │
│        Agar < bozor narxi:                            │
│        → Adminga "🔥 ARZON VARIANT!" xabari           │
│     ↓                                                  │
│     b) Obunalarni tekshiradi                          │
│        ↓                                               │
│        Mos obuna topilsa:                             │
│        → Mijozga "🔔 Sizga mos moshina!" xabari       │
│     ↓                                                  │
│  3. Listing'ni "processed" deb belgilaydi            │
└────────────────────────────────────────────────────────┘
```

**Kod (tasks/celery_tasks.py):**
```python
async def process_new_listings():
    # 1. Qayta ishlanmagan listinglar
    listings = await get_unprocessed_listings(session)
    
    for listing in listings:
        # 2a. Bozor narxi tekshirish
        if listing.is_good_deal:
            await notify_admin_about_good_deal(listing)
        
        # 2b. Obunalarni tekshirish
        temp_car = Car(
            brand=listing.brand,
            model=listing.model,
            price=listing.price
        )
        matching_subs = await find_matching_subscriptions(session, temp_car)
        
        for sub in matching_subs:
            await notify_subscriber(sub.user_id, listing)
        
        # 3. Qayta ishlangan deb belgilash
        await mark_listing_processed(session, listing.id)
```

---

### JARAYON 3️⃣: Haftalik Push Xabarnomalar

```
┌────────────────────────────────────────────────────────┐
│  HAR DUSHANBA SOAT 9:00 DA                            │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. TOP-3 eng zo'r moshinalarni tanlaydi             │
│     (is_featured=True yoki eng yangilari)             │
│     ↓                                                  │
│  2. Barcha faol userlarni oladi                       │
│     ↓                                                  │
│  3. Har bir userga xabar yuboradi:                    │
│                                                        │
│     🔥 Haftalik TOP moshinalar!                       │
│                                                        │
│     Eng zo'r takliflar:                               │
│     1. Chevrolet Malibu (2021) - 180M                 │
│     2. Toyota Camry (2020) - 250M                     │
│     3. BMW 5-series (2019) - 350M                     │
│                                                        │
│     📱 Batafsil ma'lumot uchun botga o'ting!          │
└────────────────────────────────────────────────────────┘
```

**Kod (tasks/celery_tasks.py):**
```python
@celery_app.task(name='send_weekly_push')
def send_weekly_push_task():
    # Dushanba 9:00 da ishga tushadi
    
    # 1. TOP-3 moshinalar
    cars = await get_cars(session, is_available=True, limit=3)
    
    # 2. Barcha userlar
    users = await session.execute(
        select(User).where(User.is_blocked == False)
    )
    
    # 3. Xabar yuborish
    for user in users:
        await send_push_notification(user.telegram_id, cars)
```

---

## 💾 Database Tuzilishi

### JADVALLAR VA MUNOSABATLAR:

```
┌─────────────────────────────────────────────────────┐
│                    USERS                            │
├─────────────────────────────────────────────────────┤
│  telegram_id (PK)                                   │
│  username                                           │
│  full_name                                          │
│  phone                                              │
│  is_admin                                           │
│  created_at                                         │
└─────────────────────────────────────────────────────┘
          ↓ (one-to-many)
┌─────────────────────────────────────────────────────┐
│                 SUBSCRIPTIONS                       │
├─────────────────────────────────────────────────────┤
│  id (PK)                                            │
│  user_id (FK → users)                               │
│  brand, model                                       │
│  year_from, year_to                                 │
│  price_from, price_to                               │
│  is_active                                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                     CARS                            │
├─────────────────────────────────────────────────────┤
│  id (PK)                                            │
│  brand, model, year                                 │
│  price, mileage                                     │
│  color, condition                                   │
│  transmission, fuel_type                            │
│  images (JSON)                                      │
│  is_available                                       │
│  views_count                                        │
└─────────────────────────────────────────────────────┘
          ↓ (one-to-many)
┌─────────────────────────────────────────────────────┐
│                    REVIEWS                          │
├─────────────────────────────────────────────────────┤
│  id (PK)                                            │
│  user_id (FK → users)                               │
│  car_id (FK → cars)                                 │
│  rating (1-5)                                       │
│  comment                                            │
│  created_at                                         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                   FAVORITES                         │
├─────────────────────────────────────────────────────┤
│  id (PK)                                            │
│  user_id (FK → users)                               │
│  car_id (FK → cars)                                 │
│  created_at                                         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  SOLD_CARS                          │
├─────────────────────────────────────────────────────┤
│  id (PK)                                            │
│  brand, model, year                                 │
│  purchase_price                                     │
│  selling_price                                      │
│  profit                                             │
│  sold_at                                            │
└─────────────────────────────────────────────────────┘
```

---

## 🎬 Real Misollar

### MISOL 1: Alisher Mijoz Sifatida

```
📅 DUSHANBA, 9:00
┌────────────────────────────────────────┐
│ Alisher botga /start yuboradi         │
│ → User yaratildi (ID: 123456789)      │
└────────────────────────────────────────┘

📅 9:05
┌────────────────────────────────────────┐
│ Alisher "🔍 Qidiruv" bosadi            │
│ → Filtrlar: Chevrolet, Gentra, 2020+  │
│ → 5 ta moshina topildi                │
└────────────────────────────────────────┘

📅 9:10
┌────────────────────────────────────────┐
│ Birinchi moshinani ko'rdi              │
│ → Views_count: 0 → 1                   │
│ → "❤️ Sevimlilar" bosadi               │
│ → Favorites jadvaliga qo'shildi        │
└────────────────────────────────────────┘

📅 9:15
┌────────────────────────────────────────┐
│ "⭐ Sharh yozish" bosadi                │
│ → 5 yulduz tanladi                     │
│ → "Juda yaxshi!" yozdi                 │
│ → Review saqlandi                      │
└────────────────────────────────────────┘

📅 9:20
┌────────────────────────────────────────┐
│ "🔔 Obuna" bosadi                      │
│ → Chevrolet Malibu, 2020+, 200M gacha │
│ → Subscription yaratildi               │
└────────────────────────────────────────┘

📅 SESHANBA, 14:30
┌────────────────────────────────────────┐
│ Admin yangi moshina qo'shdi:           │
│ → Chevrolet Malibu 2021, 180M         │
│ → Backend obunani topdi                │
│ → Alisher'ga xabar: "🔔 Moshina       │
│    topildi!"                           │
└────────────────────────────────────────┘

📅 15:00
┌────────────────────────────────────────┐
│ Alisher "📞 Bog'lanish" bosadi         │
│ → Admin telefoni ko'rsatildi           │
│ → Alisher qo'ng'iroq qildi             │
│ → Kelishdi va sotib oldi! 💰          │
└────────────────────────────────────────┘
```

---

### MISOL 2: Javohir Admin Sifatida

```
📅 CHORSHANBA, 10:00
┌────────────────────────────────────────┐
│ Javohir "➕ Moshina qo'shish" bosadi   │
│ → Brend: Toyota                        │
│ → Model: Camry                         │
│ → Yil: 2020                            │
│ → Narx: 250,000,000                    │
│ → Rasm yukladi                         │
│ → "✅ Ha" - tasdiqladi                 │
│ → Moshina saqlandi (ID: 91)            │
└────────────────────────────────────────┘

📅 10:01 (Avtomatik)
┌────────────────────────────────────────┐
│ Backend obunalarni tekshirdi           │
│ → 12 ta mos obuna topildi             │
│ → 12 ta mijozga xabar yuborildi        │
└────────────────────────────────────────┘

📅 14:00
┌────────────────────────────────────────┐
│ Javohir "📊 CRM Dashboard" bosadi      │
│ → Jami userlar: 1,234                  │
│ → Faol (7 kun): 456                    │
│ → Yangi (30 kun): 123                  │
│ → Konversiya: 64%                      │
└────────────────────────────────────────┘

📅 15:30
┌────────────────────────────────────────┐
│ OLX'dan arzon moshina topildi!         │
│ → Backend Javohir'ga xabar yubordi:    │
│   "🔥 ARZON VARIANT TOPILDI!"          │
│   Narx: 180M (bozor narxi: 250M)       │
│ → Javohir linkni ochdi                 │
│ → Sotuvchi bilan bog'landi             │
└────────────────────────────────────────┘
```

---

## 🔄 To'liq Data Flow

```
                    TIZIM ARXITEKTURASI
                    
┌─────────────────────────────────────────────────────────┐
│                     TELEGRAM                            │
│                  (User Interface)                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   AIOGRAM BOT                           │
│         (handlers + keyboards + states)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                  BUSINESS LOGIC                         │
│         (database/crud.py - CRUD operations)            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   POSTGRESQL                            │
│            (8 tables - permanent storage)               │
└─────────────────────────────────────────────────────────┘

                     ┌──────────────────┐
                     │      REDIS       │
                     │  (FSM storage)   │
                     └──────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    CELERY BEAT                          │
│               (Scheduler - every 5 min)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                 CELERY WORKERS                          │
│          (scraping + notifications tasks)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                PLAYWRIGHT BROWSER                       │
│           (OLX.uz + Avtoelon.uz scraping)               │
└─────────────────────────────────────────────────────────┘
```

---

## 📱 To'liq User Journey Map

```
MIJOZ SAFARI:

Start → Ro'yxat → Katalog → Moshina → Sevimli → Sharh → Obuna → Xabar → Bog'lanish → Sotib olish
  ↓       ↓         ↓         ↓         ↓        ↓       ↓       ↓        ↓           ↓
 /start  User   get_cars  car_detail favorite  review  sub   notify    contact    MAQSAD!
        yaratish           ko'rish   qo'shish  yozish  yaratish yuborish  admin     💰
```

---

## 🎯 Xulosa

**Tizim quyidagicha ishlaydi:**

1. **Mijozlar** Telegram bot orqali moshinalarni ko'radi, qidiradi, sevimlilarga qo'shadi
2. **Adminlar** bot orqali moshina qo'shadi, CRM'dan foydalanadi
3. **Backend** har 5 minutda OLX/Avtoelon'dan parse qiladi, xabarlar yuboradi
4. **Database** barcha ma'lumotlarni saqlaydi
5. **Bot** mijoz va admin o'rtasida ko'prik bo'ladi
6. **Ko'rib-savdo** telefon orqali amalga oshiriladi (to'lov tizimi yo'q)

**Hammasi avtomatik, tezkor va professional!** 🚀
