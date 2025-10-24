from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database.user import db
from handlers.Admin.states import BalanceManagementStates
from config import ADMIN_ID

router = Router()


def balance_management_kb():
    """Клавиатура управления балансом"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Выдать баланс", callback_data="give_balance")
        ],
        [
            InlineKeyboardButton(text="➖ Снять баланс", callback_data="remove_balance")
        ],
        [
            InlineKeyboardButton(text="🔍 Проверить баланс", callback_data="check_balance")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    return kb


@router.callback_query(F.data == "admin_balance")
async def admin_balance_cb(callback: types.CallbackQuery):
    """Обработка кнопки управления балансом"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Управление балансом пользователей</b>\n\n"
        "Выберите действие:",
        reply_markup=balance_management_kb()
    )


@router.callback_query(F.data == "give_balance")
async def give_balance_cb(callback: types.CallbackQuery, state: FSMContext):
    """Выдача баланса пользователю"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ <b>Выдача баланса</b>\n\n"
        "Введите User ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
        ])
    )
    
    await state.set_state(BalanceManagementStates.waiting_for_user_id_give)


@router.callback_query(F.data == "remove_balance")
async def remove_balance_cb(callback: types.CallbackQuery, state: FSMContext):
    """Снятие баланса у пользователя"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➖ <b>Снятие баланса</b>\n\n"
        "Введите User ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
        ])
    )
    
    await state.set_state(BalanceManagementStates.waiting_for_user_id_remove)


@router.callback_query(F.data == "check_balance")
async def check_balance_cb(callback: types.CallbackQuery, state: FSMContext):
    """Проверка баланса пользователя"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔍 <b>Проверка баланса</b>\n\n"
        "Введите User ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
        ])
    )
    
    await state.set_state(BalanceManagementStates.waiting_for_user_id_check)


@router.message(BalanceManagementStates.waiting_for_user_id_give)
async def process_give_user_id(message: types.Message, state: FSMContext):
    """Обработка User ID для выдачи баланса"""
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user_id=user_id)
        
        await message.answer(
            f"➕ <b>Выдача баланса пользователю {user_id}</b>\n\n"
            "Введите сумму для выдачи:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )
        
        await state.set_state(BalanceManagementStates.waiting_for_amount_give)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите корректный User ID (число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )


@router.message(BalanceManagementStates.waiting_for_user_id_remove)
async def process_remove_user_id(message: types.Message, state: FSMContext):
    """Обработка User ID для снятия баланса"""
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user_id=user_id)
        
        await message.answer(
            f"➖ <b>Снятие баланса у пользователя {user_id}</b>\n\n"
            "Введите сумму для снятия:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )
        
        await state.set_state(BalanceManagementStates.waiting_for_amount_remove)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите корректный User ID (число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )


@router.message(BalanceManagementStates.waiting_for_user_id_check)
async def process_check_user_id(message: types.Message, state: FSMContext):
    """Обработка User ID для проверки баланса"""
    try:
        user_id = int(message.text.strip())
        
        # Проверяем, существует ли пользователь
        user_exists = await db.user_exists(user_id)
        if not user_exists:
            await message.answer(
                f"❌ <b>Пользователь не найден</b>\n\n"
                f"User ID {user_id} не существует в базе данных.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
                ])
            )
            await state.clear()
            return
        
        balance = await db.get_balance(user_id)
        
        await message.answer(
            f"🔍 <b>Баланс пользователя</b>\n\n"
            f"👤 <b>User ID:</b> {user_id}\n"
            f"💰 <b>Баланс:</b> {balance} $",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
            ])
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите корректный User ID (число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )


@router.message(BalanceManagementStates.waiting_for_amount_give)
async def process_give_amount(message: types.Message, state: FSMContext):
    """Обработка суммы для выдачи баланса"""
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        user_id = data['target_user_id']
        
        if amount <= 0:
            await message.answer(
                "❌ <b>Неверная сумма</b>\n\n"
                "Сумма должна быть больше 0.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
                ])
            )
            return
        
        # Проверяем, существует ли пользователь
        user_exists = await db.user_exists(user_id)
        if not user_exists:
            await message.answer(
                f"❌ <b>Пользователь не найден</b>\n\n"
                f"User ID {user_id} не существует в базе данных.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
                ])
            )
            await state.clear()
            return
        
        # Выдаем баланс
        await db.add_balance(user_id, amount)
        new_balance = await db.get_balance(user_id)
        
        await message.answer(
            f"✅ <b>Баланс выдан успешно!</b>\n\n"
            f"👤 <b>User ID:</b> {user_id}\n"
            f"💰 <b>Выдано:</b> {amount} $\n"
            f"💰 <b>Новый баланс:</b> {new_balance} $",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
            ])
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите корректную сумму (число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )


@router.message(BalanceManagementStates.waiting_for_amount_remove)
async def process_remove_amount(message: types.Message, state: FSMContext):
    """Обработка суммы для снятия баланса"""
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        user_id = data['target_user_id']
        
        if amount <= 0:
            await message.answer(
                "❌ <b>Неверная сумма</b>\n\n"
                "Сумма должна быть больше 0.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
                ])
            )
            return
        
        # Проверяем, существует ли пользователь
        user_exists = await db.user_exists(user_id)
        if not user_exists:
            await message.answer(
                f"❌ <b>Пользователь не найден</b>\n\n"
                f"User ID {user_id} не существует в базе данных.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
                ])
            )
            await state.clear()
            return
        
        # Проверяем текущий баланс
        current_balance = await db.get_balance(user_id)
        if current_balance < amount:
            await message.answer(
                f"❌ <b>Недостаточно средств</b>\n\n"
                f"👤 <b>User ID:</b> {user_id}\n"
                f"💰 <b>Текущий баланс:</b> {current_balance} $\n"
                f"💰 <b>Попытка снять:</b> {amount} $",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
                ])
            )
            await state.clear()
            return
        
        # Снимаем баланс
        await db.add_balance(user_id, -amount)
        new_balance = await db.get_balance(user_id)
        
        await message.answer(
            f"✅ <b>Баланс снят успешно!</b>\n\n"
            f"👤 <b>User ID:</b> {user_id}\n"
            f"💰 <b>Снято:</b> {amount} $\n"
            f"💰 <b>Новый баланс:</b> {new_balance} $",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_balance")]
            ])
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите корректную сумму (число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_balance")]
            ])
        )
