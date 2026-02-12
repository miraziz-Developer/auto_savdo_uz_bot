# 🎨 Tizim Arxitekturasi - Vizual Diagramma

## 📊 Umumiy Arxitektura

```
                    ┌─────────────────────────────────────┐
                    │      👥 TELEGRAM USERS              │
                    │   (Mijozlar va Adminlar)            │
                    └────────────┬────────────────────────┘
                                 │
                    ┌────────────▼────────────────────────┐
                    │    🤖 TELEGRAM BOT (Aiogram 3.x)    │
                    │                                     │
                    │  ┌──────────┬──────────┬─────────┐ │
                    │  │ Handlers │ Keyboards│ States  │ │
                    │  └──────────┴──────────┴─────────┘ │
                    └────────────┬────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
    ┌─────────────────┐                  ┌─────────────────┐
    │  👤 CUSTOMER    │                  │  👨‍💼 ADMIN       │
    │   INTERFACE     │                  │   INTERFACE     │
    ├─────────────────┤                  ├─────────────────┤
    │ • Katalog       │                  │ • Moshina +     │
    │ • Qidiruv       │                  │ • CRM           │
    │ • Sevimlilar    │                  │ • Statistika    │
    │ • Sharh yozish  │                  │ • Murojaatlar   │
    │ • Obuna         │                  │ • Parsing       │
    └────────┬────────┘                  └────────┬────────┘
             │                                    │
             └────────────────┬───────────────────┘
                              │
                ┌─────────────▼──────────────┐
                │   💼 BUSINESS LOGIC        │
                │   (database/crud.py)       │
                │                            │
                │  • get_cars()              │
                │  • create_car()            │
                │  • add_to_favorites()      │
                │  • create_review()         │
                │  • create_subscription()   │
                └─────────────┬──────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌───────────────────┐          ┌───────────────────┐
    │   🗄️ POSTGRESQL    │          │   🔴 REDIS        │
    ├───────────────────┤          ├───────────────────┤
    │ • users           │          │ • FSM states      │
    │ • cars            │          │ • Session data    │
    │ • reviews         │          │ • Temp cache      │
    │ • favorites       │          └───────────────────┘
    │ • subscriptions   │
    │ • sold_cars       │
    │ • scraped_listings│
    │ • inquiries       │
    └───────────────────┘


┌─────────────────────────────────────────────────────────────┐
│              🔄 BACKGROUND SERVICES                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ⏰ CELERY BEAT (Scheduler)                                │
│  ├─ Every 5 min → Scraping task                            │
│  └─ Every Monday 9:00 → Push notifications                 │
│                     │                                       │
│                     ▼                                       │
│  ⚙️ CELERY WORKERS                                          │
│  ├─ scrape_websites_task()                                 │
│  ├─ process_new_listings()                                 │
│  └─ send_weekly_push()                                     │
│                     │                                       │
│     ┌───────────────┴───────────────┐                      │
│     ▼                               ▼                       │
│  🕷️ OLX SCRAPER          🕷️ AVTOELON SCRAPER               │
│  • Playwright            • Playwright                      │
│  • BeautifulSoup         • BeautifulSoup                   │
│  • Anti-detection        • Anti-detection                  │
│                                                             │
│  📊 ANALYTICS (Pandas + Matplotlib)                        │
│  • Daily sales chart                                       │
│  • Top models chart                                        │
│  • Revenue analysis                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Diagrammasi

### 1️⃣ Mijoz Moshina Qidiradi

```
┌──────┐      ┌─────┐      ┌──────────┐      ┌──────────┐      ┌────────┐
│Mijoz │─────→│ Bot │─────→│ Handler  │─────→│   CRUD   │─────→│   DB   │
└──────┘      └─────┘      │(catalog) │      │(get_cars)│      └────────┘
   │              │         └──────────┘      └──────────┘           │
   │              │                                  ▲                │
   │              │                                  │                │
   │              │         ┌──────────┐             │                │
   │              │◄────────│ Response │◄────────────┴────────────────┘
   │◄─────────────┤         └──────────┘
   │              │
```

### 2️⃣ Admin Moshina Qo'shadi

```
┌───────┐    ┌─────┐    ┌────────┐    ┌──────────┐    ┌────────┐
│ Admin │───→│ Bot │───→│  FSM   │───→│   CRUD   │───→│   DB   │
└───────┘    └─────┘    │(States)│    │(create)  │    └────────┘
                        └────────┘    └──────────┘          │
                                             │               │
                                             ▼               │
                                    ┌──────────────┐         │
                                    │Check Matching│◄────────┘
                                    │Subscriptions │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │   Notify     │
                                    │  Subscribers │
                                    └──────────────┘
```

### 3️⃣ Avtomatik Web Scraping

```
┌────────────┐      ┌──────────┐      ┌──────────┐      ┌────────┐
│Celery Beat │─────→│  Worker  │─────→│ Scraper  │─────→│ OLX.uz │
│ (5 min)    │      │  Task    │      │(Playwright)     └────────┘
└────────────┘      └────────┬─┘      └─────┬────┘
                             │               │
                             │               ▼
                             │      ┌──────────────┐
                             │      │Parse Results │
                             │      └──────┬───────┘
                             │             │
                             │             ▼
                             │      ┌──────────────┐      ┌────────┐
                             └─────→│   Save to    │─────→│   DB   │
                                    │   Database   │      └────────┘
                                    └──────────────┘
```

---

## 👥 User Interaction Flow

```
                        MIJOZ JARAYONI
                        
┌────────┐  /start  ┌──────────────────────────┐
│        │─────────→│   Botga Kirish           │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│        │          │   Asosiy Menyu           │
│        │          │   ┌─────────────────┐    │
│  M     │          │   │ 🚗 Katalog      │    │
│  I     │          │   │ 🔍 Qidiruv      │    │
│  J     │          │   │ 🔔 Obuna        │    │
│  O     │          │   │ ❤️ Sevimlilar   │    │
│  Z     │          │   └─────────────────┘    │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│        │          │  Moshina Sahifasi        │
│        │          │  ┌─────────────────┐     │
│        │          │  │ Rasm + Ma'lumot │     │
│        │          │  │ ⭐ Rating: 4.5   │     │
│        │          │  │ 👁 Views: 156    │     │
│        │          │  └─────────────────┘     │
│        │          │  ┌─────────────────┐     │
│        │          │  │ ❤️ Sevimlilar   │     │
│        │          │  │ ⭐ Sharh yozish │     │
│        │          │  │ 📞 Bog'lanish   │     │
│        │          │  └─────────────────┘     │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│        │          │   Bog'lanish             │
│        │          │   📞 Admin telefoni      │
│        │◄─────────┤   Ko'rib-savdo           │
└────────┘          └──────────────────────────┘
```

---

## 👨‍💼 Admin Workflow

```
                        ADMIN JARAYONI
                        
┌────────┐  /start  ┌──────────────────────────┐
│        │─────────→│   Admin Panel            │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│  A     │          │   Admin Menyu            │
│  D     │          │   ┌─────────────────┐    │
│  M     │          │   │ ➕ Moshina +    │    │
│  I     │          │   │ 📊 CRM          │    │
│  N     │          │   │ 📊 Statistika   │    │
│        │          │   │ 📥 Murojaatlar  │    │
│        │          │   └─────────────────┘    │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│        │          │  Moshina Qo'shish        │
│        │          │  (FSM - Step by Step)    │
│        │          │                          │
│        │          │  1. Brend?               │
│        │          │  2. Model?               │
│        │          │  3. Yil?                 │
│        │          │  4. Narx?                │
│        │          │  5. Rasm?                │
│        │          │  6. ✅ Tasdiqlash        │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│        │          │   Database'ga Saqlash    │
│        │          └────────────┬─────────────┘
│        │                       │
│        │          ┌────────────▼─────────────┐
│        │          │  Obunalarni Tekshirish   │
│        │          │  (Auto-notification)     │
│        │          └────────────┬─────────────┘
│        │                       │
│        │◄──────────────────────┘
└────────┘          Tayyor!
```

---

## 🤖 Backend Auto-Process

```
                   AVTOMATIK JARAYONLAR
                   
    CELERY BEAT                 TASKS                    ACTIONS
         │                         
         │  Every 5 min            │
         ├──────────────────────→  │
         │                         │
         │                    ┌────▼─────┐
         │                    │ Scraping │
         │                    │   Task   │
         │                    └────┬─────┘
         │                         │
         │                    ┌────▼─────────────┐
         │                    │  OLX Scraper     │
         │                    │  ├─ Parse page   │
         │                    │  ├─ Get listings │
         │                    │  └─ Save to DB   │
         │                    └────┬─────────────┘
         │                         │
         │                    ┌────▼─────────────┐
         │                    │ Avtoelon Scraper │
         │                    │  ├─ Parse page   │
         │                    │  ├─ Get listings │
         │                    │  └─ Save to DB   │
         │                    └────┬─────────────┘
         │                         │
         │                    ┌────▼─────────────┐
         │                    │ Process Listings │
         │                    │  ├─ Check price  │
         │                    │  ├─ Find matches │
         │                    │  └─ Send alerts  │
         │                    └──────────────────┘
         │                         
         │  Monday 9:00            │
         ├──────────────────────→  │
         │                         │
         │                    ┌────▼─────────┐
         │                    │  Push Task   │
         │                    └────┬─────────┘
         │                         │
         │                    ┌────▼─────────────┐
         │                    │ Send to All Users│
         │                    │ (TOP-3 cars)     │
         │                    └──────────────────┘
```

---

## 📊 Database Schema Visual

```
┌─────────────────────────┐
│        USERS            │
├─────────────────────────┤
│ telegram_id (PK)        │
│ username                │
│ full_name               │
│ phone                   │
│ is_admin                │
│ created_at              │
└────────┬────────────────┘
         │ 1
         │
         │ Many
         ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│    SUBSCRIPTIONS        │       │       FAVORITES         │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │       │ id (PK)                 │
│ user_id (FK)            │       │ user_id (FK)            │
│ brand                   │       │ car_id (FK)             │
│ model                   │       │ created_at              │
│ year_from, year_to      │       └────────┬────────────────┘
│ price_from, price_to    │                │
│ is_active               │                │ Many
└─────────────────────────┘                │
                                           │ 1
                                           ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│        REVIEWS          │       │         CARS            │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │       │ id (PK)                 │
│ user_id (FK)            │       │ brand, model            │
│ car_id (FK)             │◄──────┤ year, price             │
│ rating (1-5)            │ Many  │ mileage, color          │
│ comment                 │       │ transmission, fuel_type │
│ created_at              │       │ images (JSON)           │
└─────────────────────────┘       │ is_available            │
                                  │ views_count             │
                                  └─────────────────────────┘

┌─────────────────────────┐       ┌─────────────────────────┐
│     SOLD_CARS           │       │   SCRAPED_LISTINGS      │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │       │ id (PK)                 │
│ brand, model, year      │       │ source (olx/avtoelon)   │
│ purchase_price          │       │ external_id             │
│ selling_price           │       │ url, title              │
│ profit                  │       │ brand, model, year      │
│ sold_at                 │       │ price, images           │
│ buyer_id (FK)           │       │ is_processed            │
└─────────────────────────┘       │ is_good_deal            │
                                  └─────────────────────────┘
```

---

## 🎯 Complete Request-Response Cycle

```
USER ACTION                 BOT                 DATABASE              RESPONSE

   │                         │                      │                     │
   │  "🚗 Katalog"           │                      │                     │
   ├────────────────────────→│                      │                     │
   │                         │                      │                     │
   │                         │  SELECT * FROM cars  │                     │
   │                         ├─────────────────────→│                     │
   │                         │                      │                     │
   │                         │  ◄─── cars list ─────┤                     │
   │                         │                      │                     │
   │                         │  Format + Photo      │                     │
   │                         │─────────────────────────────────────────→  │
   │                         │                      │                     │
   │  ❤️ Click               │                      │                     │
   ├────────────────────────→│                      │                     │
   │                         │                      │                     │
   │                         │ INSERT INTO favorites│                     │
   │                         ├─────────────────────→│                     │
   │                         │                      │                     │
   │                         │  ◄─── Success ───────┤                     │
   │                         │                      │                     │
   │  ◄─── "❤️ Qo'shildi!" ──┤                      │                     │
   │                         │                      │                     │
```

---

## 🔐 Security & Performance

```
┌───────────────────────────────────────────────────┐
│              SECURITY LAYERS                      │
├───────────────────────────────────────────────────┤
│                                                   │
│  1. Admin Check                                   │
│     └─ settings.admin_list                        │
│                                                   │
│  2. Database Validation                           │
│     └─ Foreign Keys, Constraints                  │
│                                                   │
│  3. FSM State Management                          │
│     └─ Redis session isolation                    │
│                                                   │
│  4. Anti-Bot Protection (Scraping)                │
│     └─ User-agent rotation                        │
│     └─ Random delays                              │
│     └─ Playwright stealth                         │
│                                                   │
└───────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────┐
│           PERFORMANCE OPTIMIZATION                │
├───────────────────────────────────────────────────┤
│                                                   │
│  1. Async Operations                              │
│     └─ All DB queries async                       │
│                                                   │
│  2. Redis Caching                                 │
│     └─ FSM states fast access                     │
│                                                   │
│  3. Database Indexing                             │
│     └─ Primary keys, Foreign keys                 │
│                                                   │
│  4. Background Processing                         │
│     └─ Celery workers (non-blocking)              │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## 📈 Monitoring & Analytics

```
┌────────────────────────────────────────────────────┐
│                 WHAT WE TRACK                      │
├────────────────────────────────────────────────────┤
│                                                    │
│  USER METRICS:                                     │
│  • Total users                                     │
│  • Active users (7 days)                           │
│  • New users (30 days)                             │
│  • Conversion rate (phone provided)                │
│                                                    │
│  CAR METRICS:                                      │
│  • Total cars                                      │
│  • Available cars                                  │
│  • Views per car                                   │
│  • Average rating                                  │
│                                                    │
│  BUSINESS METRICS:                                 │
│  • Sales count                                     │
│  • Revenue                                         │
│  • Profit                                          │
│  • Best selling models                             │
│                                                    │
│  ENGAGEMENT METRICS:                               │
│  • Subscriptions count                             │
│  • Favorites count                                 │
│  • Reviews count                                   │
│  • Inquiries count                                 │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

# 🎓 Xulosa

Tizim **3 qatlamli arxitektura** asosida qurilgan:

1. **Presentation Layer** (Telegram Bot Interface)
   - User handlers
   - Admin handlers
   - Keyboards & States

2. **Business Logic Layer** (CRUD Operations)
   - Database operations
   - Matching algorithms
   - Data processing

3. **Data Layer** (PostgreSQL + Redis)
   - Permanent storage
   - Temporary storage (FSM)

4. **Background Layer** (Celery)
   - Scheduled tasks
   - Async operations

**Barcha qismlar bir-biriga bog'langan va professional tarzda ishlaydi!** 🚀
