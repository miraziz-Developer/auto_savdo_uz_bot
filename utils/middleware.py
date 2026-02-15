from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database.database import async_session_maker
from database.crud import get_or_create_user
from loguru import logger

import time

class BlockCheckMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.cache = {}  # {user_id: (is_blocked, timestamp)}
        self.ttl = 60    # Cache TTL in seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        
        # Check cache
        current_time = time.time()
        cached = self.cache.get(user.id)
        
        if cached and (current_time - cached[1] < self.ttl):
            is_blocked = cached[0]
            if is_blocked:
                if isinstance(event, Message):
                    await event.answer("🚫 <b>Siz botdan bloklangansiz!</b>\nAdmin bilan bog'laning: @avtosavdo_admin", parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Siz bloklangansiz!", show_alert=True)
                return
            # If not blocked in cache, proceed without DB call
            return await handler(event, data)

        async with async_session_maker() as session:
            # We fetch user here anyway because get_or_create_user also updates last_activity
            # which we optimized in crud.py to only write every 60s
            db_user = await get_or_create_user(session, user.id)
            
            is_blocked = db_user.is_blocked if db_user else False
            
            # Update cache
            self.cache[user.id] = (is_blocked, current_time)
            
            # Evict expired cache entries (avoid full flush)
            if len(self.cache) > 5000:
                expired_keys = [
                    uid for uid, (_, ts) in self.cache.items()
                    if current_time - ts >= self.ttl
                ]
                for uid in expired_keys:
                    del self.cache[uid]

            if is_blocked:
                if isinstance(event, Message):
                    await event.answer("🚫 <b>Siz botdan bloklangansiz!</b>\nAdmin bilan bog'laning: @avtosavdo_admin", parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Siz bloklangansiz!", show_alert=True)
                return

        return await handler(event, data)
