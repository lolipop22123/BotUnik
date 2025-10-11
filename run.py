import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, RATE_LIMIT_PER_MIN, ADMIN_ID
from handlers import start, help, echo
from handlers.User import profile, videoprocessing
from handlers.Admin import media_manager, broadcast, statistics, subscriptions

from services.commands import setup_bot_commands
from middlewares.logging import LoggingMiddleware
from middlewares.throttling import ThrottlingMiddleware

# Отдельный роутер для админских хендлеров 
from aiogram import Router
from middlewares.admin_gate import AdminGateMiddleware

from aiogram.filters import Command
from aiogram import types
from services.logger import setup_logging
from database.user import db

from dotenv import load_dotenv

load_dotenv()


admin_router = Router(name="admin")

@admin_router.message(Command("admin_ping"))
async def admin_ping(message: types.Message):
    await message.answer("✅ Admin OK")


BOT_TOKEN = os.getenv("BOT_TOKEN", "your_token_here")

async def on_startup(bot: Bot):
    await db.connect()


async def on_shutdown(bot: Bot):
    await db.close()


async def main():
    setup_logging()
    
    # 1) Подключаемся к БД заранее
    await db.connect()
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Добавляем хранилище состояний для FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)


    # Подключаем глобальные middleware
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_per_min=RATE_LIMIT_PER_MIN))


    # Роутер админа — защищаем миддлварью
    admin_router.message.middleware(AdminGateMiddleware(admin_id=ADMIN_ID))


    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(admin_router)
    dp.include_router(media_manager.router)  # Админская панель медиа
    dp.include_router(broadcast.router)  # Админская панель рассылки
    dp.include_router(statistics.router)  # Админская панель статистики
    dp.include_router(subscriptions.router)  # Админская панель подписок
    dp.include_router(echo.router)
    dp.include_router(profile.router)
    dp.include_router(videoprocessing.router)
    
    # Устанавливаем меню-команды в Telegram (видны в боковом меню)
    await setup_bot_commands(bot)

    print("🤖 Бот запущен…")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # 2) Корректно закрываем пул
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())