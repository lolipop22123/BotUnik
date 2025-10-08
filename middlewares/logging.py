from aiogram.types import Message
from aiogram import BaseMiddleware

from loguru import logger
from typing import Any, Callable, Dict, Awaitable


class LoggingMiddleware(BaseMiddleware):
    """Логирует входящие сообщения: кто, что, когда."""


    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        logger.info(
        f"msg from={user.id} (@{user.username}) name={user.full_name} text={event.text!r}"
        )
        
        return await handler(event, data)