from aiogram import Router, types
from aiogram.filters import Command


# Роутер для команды /help
router = Router()


# Команда /help
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Вот список команд:\n/start — начать\n/help — помощь")
