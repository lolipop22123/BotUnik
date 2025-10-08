import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode


from config import BOT_TOKEN, RATE_LIMIT_PER_MIN, ADMIN_ID
from handlers import start, help, echo
from services.commands import setup_bot_commands
from middlewares.logging import LoggingMiddleware
from middlewares.throttling import ThrottlingMiddleware


# Отдельный роутер для админских хендлеров (пример)
from aiogram import Router
from middlewares.admin_gate import AdminGateMiddleware


admin_router = Router(name="admin")
# Пример админ-хендлера (скрытый): /admin_ping
from aiogram.filters import Command
from aiogram import types


@admin_router.message(Command("admin_ping"))
async def admin_ping(message: types.Message):
await message.answer("✅ Admin OK")


async def main():
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# Подключаем глобальные middleware
dp.message.middleware(LoggingMiddleware())
dp.message.middleware(ThrottlingMiddleware(rate_per_min=RATE_LIMIT_PER_MIN))


# Роутер админа — защищаем миддлварью
admin_router.message.middleware(AdminGateMiddleware(admin_id=ADMIN_ID))


# Подключаем роутеры
dp.include_router(start.router)
dp.include_router(help.router)
dp.include_router(admin_router)
dp.include_router(echo.router)


# Устанавливаем меню-команды в Telegram (видны в боковом меню)
await setup_bot_commands(bot)


print("🤖 Бот запущен…")
await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
asyncio.run(main())