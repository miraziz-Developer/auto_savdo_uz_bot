import asyncio
import sys
import os

# Add project root to python path
sys.path.append(os.getcwd())

from sqlalchemy import text
from database.database import engine

async def migrate():
    print("Starting migration...")
    try:
        async with engine.begin() as conn:
            # Add new columns to scraped_listings
            await conn.execute(text("ALTER TABLE scraped_listings ADD COLUMN IF NOT EXISTS mileage INTEGER"))
            await conn.execute(text("ALTER TABLE scraped_listings ADD COLUMN IF NOT EXISTS description TEXT"))
            await conn.execute(text("ALTER TABLE scraped_listings ADD COLUMN IF NOT EXISTS location VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE scraped_listings ADD COLUMN IF NOT EXISTS color VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE scraped_listings ADD COLUMN IF NOT EXISTS transmission VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE scraped_listings ADD COLUMN IF NOT EXISTS fuel_type VARCHAR(50)"))
            print("Successfully added columns to scraped_listings")
            
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
