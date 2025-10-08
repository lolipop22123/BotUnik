from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from datetime import datetime, timedelta

from database.user import db
from keyboards.kb_user import profile_reply_kb, main_reply_kb


router = Router()


@router.callback_query(F.data == "videoprcess")
async def videoprcess_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    balance = await db.get_balance(user_id)
    
    if await db.has_subscription(user_id) == False:
        await callback.message.answer(
            "🚫 <b>У вас нет подписки</b>\n\n"
            "Пожалуйста, купите подписку для обработки видео."
        )
    else:
        if await db.is_subscription_active(user_id) == False:
            await callback.message.answer(
                "🚫 <b>Ваша подписка истекла</b>\n\n"
                "Пожалуйста, купите подписку для обработки видео."
            )
        else:
            await callback.message.answer(
                "У вас есть подписка, но она истекла. Пожалуйста, купите подписку для обработки видео."
            )