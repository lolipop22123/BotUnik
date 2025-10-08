# middlewares/admin_gate.py
from typing import Any, Awaitable, Callable, Dict
from aiogram.types import TelegramObject, Message

class AdminGateMiddleware:
    """Пускает дальше только ADMIN_ID. Использовать на message-роутере."""
    def __init__(self, admin_id: int | None) -> None:
        self.admin_id = admin_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Для message-роутера event будет Message
        msg = event if isinstance(event, Message) else data.get("event_message")

        user_id = None
        if isinstance(msg, Message) and msg.from_user:
            user_id = msg.from_user.id

        # Если админ не задан — никого не блокируем
        if not self.admin_id:
            return await handler(event, data)

        if user_id == self.admin_id:
            return await handler(event, data)

        if isinstance(msg, Message):
            await msg.answer("🚫 Доступ только для админа.")
        return
