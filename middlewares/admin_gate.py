from aiogram import BaseMiddleware
from aiogram.types import Message

from typing import Any, Callable, Dict, Awaitable


class AdminGateMiddleware(BaseMiddleware):
    """Проверка, что сообщение — от ADMIN_ID. Иначе — отклоняем.
    Используй на отдельных роутерах (admin_router) или конкретных хендлерах.
    """


    def __init__(self, admin_id: int | None) -> None:
        self.admin_id = admin_id

        async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any],
        ) -> Any:
            if self.admin_id and event.from_user and event.from_user.id == self.admin_id:
                return await handler(event, data)
            
            # Мягко откажем, но не поднимем исключение
            await event.answer("🚫 Доступ только для админа.")
            return