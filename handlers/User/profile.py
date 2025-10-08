from aiogram import Router, types, F
from aiogram.filters import Command

from database.user import db
from keyboards.kb_user import profile_reply_kb, main_reply_kb

router = Router()


@router.callback_query(F.data == "profile")
async def profile_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    balance = await db.get_balance(user_id)
    
    await callback.message.answer(
        f"🚹 Профиль\n"
        f"👤 Имя: {username}\n"
        f"💰 Баланс: {balance} ₽",
        reply_markup=profile_reply_kb()
    )


@router.callback_query(F.data == "balanceadd")
async def balanceadd_cb(callback: types.CallbackQuery):
    pass


@router.callback_query(F.data == "backstart")
async def backstart_cb(callback: types.CallbackQuery):
    await callback.message.answer(
        f"<b>Привет! Я бот</b> 🚀\n"
        "Используй кнопки ниже или /help для списка команд.",
        reply_markup=main_reply_kb()
    )