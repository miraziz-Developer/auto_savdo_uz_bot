"""
Follow-up System — Optimized v2
Batch processing, single commit, flood control
"""
import asyncio
from datetime import datetime
from loguru import logger
from aiogram import Bot

from config import settings
from database.database import async_session_maker
from database.crud import get_pending_followups, mark_followup_sent


async def process_pending_followups(bot: Bot) -> dict:
    """
    Pending follow-up'larni batch usulida yuboradi.
    - Bitta session ishlatadi
    - Telegram flood limit: 0.05s oraliq (20 msg/sek max)
    - Bloklangan foydalanuvchilar avtomatik o'chiriladi
    """
    try:
        async with async_session_maker() as session:
            pending = await get_pending_followups(session)

            if not pending:
                return {'processed': 0, 'failed': 0}

            sent_count = 0
            failed_count = 0
            to_mark_sent = []   # Batch mark uchun ID lar

            for followup in pending:
                try:
                    await bot.send_message(
                        chat_id=followup.user_id,
                        text=followup.message_text or "...",
                        parse_mode="HTML"
                    )
                    to_mark_sent.append(followup.id)
                    sent_count += 1

                    # Flood protection: 30ms oraliq
                    await asyncio.sleep(0.3)

                except Exception as e:
                    err_str = str(e).lower()
                    failed_count += 1

                    # Bloklangan bot — keyinchalik ham yuborish shart emas
                    if "forbidden" in err_str or "blocked" in err_str or "deactivated" in err_str:
                        to_mark_sent.append(followup.id)
                        logger.debug(f"User {followup.user_id} blocked bot — marking as sent")
                    else:
                        logger.warning(f"Follow-up {followup.id} failed: {e}")

            # Batch mark — bitta commit
            if to_mark_sent:
                from sqlalchemy import update
                from database.models import FollowUp
                await session.execute(
                    update(FollowUp)
                    .where(FollowUp.id.in_(to_mark_sent))
                    .values(is_sent=True, sent_at=datetime.utcnow())
                )
                await session.commit()

        if sent_count > 0 or failed_count > 0:
            logger.info(f"Follow-ups: ✅ {sent_count} sent, ❌ {failed_count} failed")

        return {'processed': sent_count, 'failed': failed_count}

    except Exception as e:
        logger.error(f"Follow-up system error: {e}")
        return {'error': str(e), 'processed': 0, 'failed': 0}


async def send_admin_digest(bot: Bot):
    """
    Admin'ga kunlik digest xabari — pending va hot leads
    """
    try:
        async with async_session_maker() as session:
            from database.crud import get_pending_inquiries, get_pending_buy_requests, get_hot_leads

            # Parallel queries
            pending_inquiries, pending_buys, hot_leads = await asyncio.gather(
                get_pending_inquiries(session),
                get_pending_buy_requests(session),
                get_hot_leads(session, min_score=60, limit=5),
            )

        urgency_map = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}

        text = (
            f"🌅 <b>KUNLIK DIGEST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📥 <b>Kutayotgan murojaatlar: {len(pending_inquiries)}</b>\n"
        )
        for inq in pending_inquiries[:3]:
            em = urgency_map.get(inq.urgency, "⚪")
            text += f"   {em} #{inq.id} — {inq.inquiry_type} (Ball: {inq.lead_score})\n"
        if len(pending_inquiries) > 3:
            text += f"   <i>... va yana {len(pending_inquiries) - 3} ta</i>\n"

        text += f"\n🛒 <b>Sotib olish arizalari: {len(pending_buys)}</b>\n"
        for req in pending_buys[:3]:
            text += f"   📋 #{req.id} — {req.brand or '-'} {req.model or '-'} (Ball: {req.lead_score})\n"
        if len(pending_buys) > 3:
            text += f"   <i>... va yana {len(pending_buys) - 3} ta</i>\n"

        text += f"\n🔥 <b>Hot leads (60+ ball):</b>\n"
        for user in hot_leads:
            name = user.full_name or user.username or f"ID: {user.telegram_id}"
            text += f"   🔥 {name} — Ball: {user.lead_score}\n"
        if not hot_leads:
            text += "   <i>Hozircha yo'q</i>\n"

        text += f"\n⏰ <i>{datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC</i>"

        for admin_id in settings.admin_list:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Digest to admin {admin_id} failed: {e}")

    except Exception as e:
        logger.error(f"Admin digest error: {e}")
