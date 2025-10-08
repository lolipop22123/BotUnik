import time

from aiogram.types import Message
from aiogram import BaseMiddleware

from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict, Awaitable


class ThrottlingMiddleware(BaseMiddleware):
    """Простой антифлуд: ограничение N сообщений/минуту на пользователя."""


    def __init__(self, rate_per_min: int = 20) -> None:
        self.rate_per_min = max(1, rate_per_min)
        self._hits: Dict[int, Deque[float]] = defaultdict(deque)


    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        now = time.time()
        uid = event.from_user.id if event.from_user else 0
        window = 60.0
        q = self._hits[uid]


        # Очистка устаревших обращений
        while q and (now - q[0]) > window:
            q.popleft()


        if len(q) >= self.rate_per_min:
            # Превышен лимит — мягко сообщаем и глотаем событие
            await event.answer("⏳ Слишком часто. Попробуй через пару секунд…")
            return


        q.append(now)
        return await handler(event, data)