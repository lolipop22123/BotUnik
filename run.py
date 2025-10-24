import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, RATE_LIMIT_PER_MIN, ADMIN_ID
from handlers import start, help, echo
from handlers.User import profile, videoprocessing, batch_processing
from handlers.Admin import media_manager, broadcast, statistics, subscriptions, balance_manager

from services.commands import setup_bot_commands
from services.subscription_checker import start_subscription_checker, stop_subscription_checker
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
    print("DB pool ready ✅")

async def on_shutdown(bot: Bot):
    await db.close()
    print("DB pool closed")

async def main():
    setup_logging()
    
    # 1) Подключаемся к БД заранее
    await db.connect()
    
    # Синхронизируем музыку из папки
    music_folder = "music"
    if os.path.exists(music_folder):
        added_count = await db.sync_music_from_folder(music_folder)
        print(f"🎵 Синхронизировано {added_count} музыкальных файлов из папки {music_folder}")
    
    # Синхронизируем шрифты из папки
    fonts_folder = "fonts"
    if os.path.exists(fonts_folder):
        added_count = await db.sync_fonts_from_folder(fonts_folder)
        print(f"🔤 Синхронизировано {added_count} шрифтов из папки {fonts_folder}")
    
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
    dp.include_router(balance_manager.router)  # Админская панель баланса
    dp.include_router(echo.router)
    dp.include_router(profile.router)
    dp.include_router(videoprocessing.router)
    dp.include_router(batch_processing.router)
    
    # Устанавливаем меню-команды в Telegram (видны в боковом меню)
    await setup_bot_commands(bot)

    print("🤖 Бот запущен…")
    
    # Запускаем фоновую проверку подписок
    subscription_task = asyncio.create_task(start_subscription_checker())
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Останавливаем фоновую задачу
        await stop_subscription_checker()
        subscription_task.cancel()
        try:
            await subscription_task
        except asyncio.CancelledError:
            pass
        
        # Корректно закрываем пул
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())