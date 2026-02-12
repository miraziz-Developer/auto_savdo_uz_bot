"""
Handlers for analytics and statistics
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from database.database import async_session_maker
from database.crud import get_market_stats

router = Router()

@router.message(F.text.in_(["📊 Statistika", "📊 Bozor statistikasi"]))
async def show_statistics(message: Message):
    """Show market statistics"""
    async with async_session_maker() as session:
        stats = await get_market_stats(session)
        
    if not stats:
        await message.answer("Hozircha statistika ma'lumotlari yig'ilmoqda...")
        return
        
    text = f"""
📊 <b>BOZOR STATISTIKASI</b>

🏪 Jami e'lonlar: <b>{stats['total_listings']} ta</b>
🔥 Bugungi yangi e'lonlar: <b>{stats['new_today']} ta</b>

📉 <b>O'rtacha narxlar (Top modellar):</b>
"""
    
    for model, price in stats['avg_prices'].items():
        text += f"▪️ {model}: <b>{price:,.0f} $</b>\n"
        
    text += f"""
💡 <i>Ma'lumotlar so'nggi 24 soat ichida yangilangan.</i>
"""
    
    await message.answer(text, parse_mode="HTML")
