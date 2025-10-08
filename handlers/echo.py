from aiogram import Router, types


# Роутер для команды /echo
router = Router()


# Команда /echo
@router.message()
async def echo_message(message: types.Message):
    await message.answer(f"Ты сказал: {message.text}")
