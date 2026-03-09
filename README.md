# AvtoSavdo Telegram Bot

🚗 Professional Telegram bot for car sales business in Uzbekistan

## Features

### For Customers
- 🚗 **Car Catalog** - Browse available cars with filters
- 🔍 **Smart Search** - Find cars by brand, model, year, price
- 🔔 **Subscriptions** - Get notified when matching cars are added
- 💰 **Sell Your Car** - Submit car selling requests

### For Admins
- ➕ **Add Cars** - Quick car listing creation
- 📊 **Analytics** - Sales statistics and charts
- 💰 **Record Sales** - Track sold cars and profits
- 📥 **Manage Inquiries** - Handle customer requests
- 🔍 **Parsing Dashboard** - Monitor OLX and Avtoelon listings
- 📢 **Broadcast** - Send messages to all users

### Backend Features
- 🕷️ **Web Scraping** - Auto-scrape OLX.uz and Avtoelon.uz every 5 minutes
- 🔔 **Smart Notifications** - Auto-notify users about matching cars
- 📊 **Analytics** - Sales charts with pandas & matplotlib
- 📤 **Auto Publishing** - Post to Telegram channel and Instagram
- 🔄 **Task Scheduling** - Celery-based periodic tasks

## Tech Stack

- **Bot Framework**: Aiogram 3.x
- **Database**: PostgreSQL with SQLAlchemy (async)
- **FSM Storage**: Redis
- **Web Scraping**: Playwright + BeautifulSoup
- **Task Queue**: Celery + Redis
- **Analytics**: pandas + matplotlib
- **Logging**: loguru

## Installation

### 1. Clone and Setup

```bash
cd /Users/mirazizerkinaliyev_dev/Documents/avtosavdouz
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Setup PostgreSQL

```bash
# Install PostgreSQL (macOS)
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb avtosavdo_bot
```

### 4. Setup Redis

```bash
# Install Redis (macOS)
brew install redis
brew services start redis
```

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
- `BOT_TOKEN` - Get from @BotFather
- `ADMIN_IDS` - Comma-separated admin Telegram IDs
- `DB_PASSWORD` - PostgreSQL password
- `TELEGRAM_CHANNEL_ID` - Your channel username (@channel)

## Running

### 1. Start the Bot

```bash
python bot.py
```

### 2. Start Celery Worker (in separate terminal)

```bash
celery -A tasks.celery_tasks worker --loglevel=info
```

### 3. Start Celery Beat (in separate terminal)

```bash
celery -A tasks.celery_tasks beat --loglevel=info
```

## Project Structure

```
avtosavdouz/
├── bot.py                  # Main bot application
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
│
├── database/
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # Database connection
│   └── crud.py            # CRUD operations
│
├── handlers/
│   ├── common.py          # Common handlers (/start, /help)
│   ├── catalog.py         # Car catalog & search
│   ├── subscriptions.py   # Subscription management
│   └── admin.py           # Admin operations
│
├── keyboards/
│   ├── user_keyboards.py  # User interface keyboards
│   └── admin_keyboards.py # Admin interface keyboards
│
├── states/
│   └── states.py          # FSM states
│
├── scrapers/
│   ├── base_scraper.py    # Base scraper class
│   ├── olx_scraper.py     # OLX.uz scraper
│   ├── avtoelon_scraper.py # Avtoelon.uz scraper
│   └── scraper_manager.py  # Scraper coordinator
│
├── analytics/
│   └── sales_analytics.py # Sales analytics & charts
│
├── tasks/
│   └── celery_tasks.py    # Celery periodic tasks
│
├── utils/
│   └── notifications.py   # Notification utilities
│
└── scripts/
    ├── run_scraper.py     # Manual scraper test
    └── generate_analytics.py # Manual analytics generation
```

## Usage Examples

### Testing Scrapers

```bash
# Run manual scraper test
python scripts/run_scraper.py

# Choose:
# 1. Only OLX
# 2. Only Avtoelon  
# 3. All scrapers

# Results saved to JSON files
```

### Generate Analytics

```bash
python scripts/generate_analytics.py

# Creates charts in analytics/reports/
```

### Database Migrations

```bash
# If using Alembic (optional)
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Features Roadmap

- [x] Basic bot functionality
- [x] Car catalog with filters
- [x] User subscriptions
- [x] Admin panel
- [x] Web scraping (OLX + Avtoelon)
- [x] Sales analytics
- [x] Celery task scheduling
- [ ] Instagram auto-posting
- [ ] Payment integration
- [ ] Car favorites
- [ ] Advanced filters (transmission, fuel type, etc.)
- [ ] Image gallery for cars
- [ ] User reviews
- [ ] CRM dashboard

## Monitoring

### Logs

- Bot logs: `logs/bot_YYYY-MM-DD.log`
- Celery logs: Check terminal output

### Health Check

```bash
# Check PostgreSQL
psql -U postgres -d avtosavdo_bot -c "SELECT COUNT(*) FROM users;"

# Check Redis
redis-cli ping

# Check Celery
celery -A tasks.celery_tasks inspect active
```

## Troubleshooting

### Scraper Issues

If scraping fails:
1. Check internet connection
2. Sites may have changed HTML structure
3. Try with `headless=False` to see browser
4. Check user-agent rotation

### Database Issues

```bash
# Reset database (WARNING: deletes all data)
dropdb avtosavdo_bot
createdb avtosavdo_bot
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())"
```

## Contributing

This is a custom project. For improvements:
1. Test thoroughly
2. Follow existing code style
3. Update documentation

## License

Private project - All rights reserved

