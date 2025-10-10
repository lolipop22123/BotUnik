from aiogram import Router, types
from aiogram.filters import CommandStart

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
    
    # Проверяем, является ли пользователь админом
    is_admin = message.from_user.id == ADMIN_ID
        
    await message.answer(
        f"<b>Привет! Я бот</b> 🚀\n"
        "Используй кнопки ниже или /help для списка команд.",
        reply_markup=main_reply_kb(is_admin=is_admin)
    )
    
