"""
Follow-up System — Avtomatik xabar yuborish tizimi
Celery task orqali ishlamoqda: pending follow-uplarni tekshirib, yuboradi.
"""
import asyncio
from datetime import datetime
from loguru import logger
from aiogram import Bot

from config import settings
from database.database import async_session_maker
from database.crud import (
    get_pending_followups, mark_followup_sent,
    get_inquiries_needing_followup, get_buy_requests_needing_followup
)


async def process_pending_followups(bot: Bot):
    """
    Barcha pending follow-up'larni tekshirib, yuboradi.
    Bu funksiya scheduler yoki celery task tomonidan chaqiriladi.
    """
    try:
        async with async_session_maker() as session:
            pending = await get_pending_followups(session)
        
        if not pending:
            return {'processed': 0}
        
        sent_count = 0
        failed_count = 0
        
        for followup in pending:
            try:
                # Send message to user
                await bot.send_message(
                    chat_id=followup.user_id,
                    text=followup.message_text,
                    parse_mode="HTML"
                )
                
                # Mark as sent
                async with async_session_maker() as session:
                    await mark_followup_sent(session, followup.id)
                
                sent_count += 1
                logger.info(
                    f"Follow-up sent: type={followup.message_type}, "
                    f"user={followup.user_id}, target={followup.target_type}#{followup.target_id}"
                )
                
                # Small delay to avoid flooding
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send follow-up {followup.id}: {e}")
                
                # If user blocked the bot, mark as sent to avoid repeated attempts
                if "Forbidden" in str(e) or "blocked" in str(e).lower():
                    async with async_session_maker() as session:
                        await mark_followup_sent(session, followup.id)
        
        logger.info(f"Follow-ups processed: sent={sent_count}, failed={failed_count}")
        return {'processed': sent_count, 'failed': failed_count}
    
    except Exception as e:
        logger.error(f"Error processing follow-ups: {e}")
        return {'error': str(e)}


async def send_admin_digest(bot: Bot):
    """
    Har kuni ertalab admin'ga digest yuboradi:
    - Yangi murojaatlar
    - Follow-up kerak bo'lgan arizalar
    - Hot leads
    """
    try:
        async with async_session_maker() as session:
            from database.crud import get_pending_inquiries, get_pending_buy_requests, get_hot_leads
            
            pending_inquiries = await get_pending_inquiries(session)
            pending_buys = await get_pending_buy_requests(session)
            hot_leads = await get_hot_leads(session, min_score=60, limit=5)
        
        text = "🌅 <b>KUNLIK DIGEST</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Pending inquiries
        text += f"📥 <b>Kutayotgan murojaatlar: {len(pending_inquiries)}</b>\n"
        for inq in pending_inquiries[:3]:
            urgency_emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}.get(inq.urgency, "⚪")
            text += f"   {urgency_emoji} #{inq.id} — {inq.inquiry_type} (Ball: {inq.lead_score})\n"
        if len(pending_inquiries) > 3:
            text += f"   <i>... va yana {len(pending_inquiries) - 3} ta</i>\n"
        
        text += "\n"
        
        # Buy requests
        text += f"🛒 <b>Sotib olish arizalari: {len(pending_buys)}</b>\n"
        for req in pending_buys[:3]:
            text += f"   📋 #{req.id} — {req.brand or '-'} {req.model or '-'} (Ball: {req.lead_score})\n"
        if len(pending_buys) > 3:
            text += f"   <i>... va yana {len(pending_buys) - 3} ta</i>\n"
        
        text += "\n"
        
        # Hot leads
        text += f"🔥 <b>Hot leads (60+ ball):</b>\n"
        for user in hot_leads:
            name = user.full_name or user.username or f"ID: {user.telegram_id}"
            text += f"   🔥 {name} — Ball: {user.lead_score}\n"
        
        if not hot_leads:
            text += "   <i>Hozircha yo'q</i>\n"
        
        text += f"\n⏰ <i>{datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC</i>"
        
        for admin_id in settings.admin_list:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error sending digest to admin {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"Error generating admin digest: {e}")
