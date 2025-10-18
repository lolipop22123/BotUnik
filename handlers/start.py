from aiogram import Router, types
from aiogram.filters import CommandStart, Command

from loguru import logger

from database.user import db
from keyboards.kb_user import main_reply_kb
from config import ADMIN_ID

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    
    user_exists = await db.user_exists(message.from_user.id)
    
    if user_exists == False:
        await db.add_user(message.from_user.id, message.from_user.username)
        logger.info(f"User {message.from_user.id} - {message.from_user.username} добавлен в базу данных")
    else:
        logger.info(f"{message.from_user.id} - {message.from_user.username} уже есть в базе данных")
        
    await message.answer(
        f"<b>Привет! Я бот</b> 🚀\n"
        "Используй кнопки ниже или /help для списка команд.",
        reply_markup=main_reply_kb()
    )


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Команда для открытия админ панели"""
    
    # Проверка прав админа
    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "❌ <b>Доступ запрещен</b>\n\n"
            "Эта команда доступна только администратору."
        )
        return
    
    # Импортируем функцию админской клавиатуры
    from handlers.Admin.media_manager import admin_main_kb
    
    # Статистика для админа
    users_count = await db.count_users()
    active_subs = (await db.get_subscription_statistics())['active']
    
    await message.answer(
        f"👨‍💼 <b>Админ панель</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📝 Активных подписок: {active_subs}\n\n"
        "Выберите раздел для управления:",
        reply_markup=admin_main_kb()
    )
    
