from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from database.user import db
from handlers.Admin.states import SubscriptionManagementStates
from config import ADMIN_ID

router = Router()


def subscription_management_kb():
    """Клавиатура управления подписками"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Выдать подписку", callback_data="give_subscription")
        ],
        [
            InlineKeyboardButton(text="➖ Забрать подписку", callback_data="remove_subscription")
        ],
        [
            InlineKeyboardButton(text="🔍 Проверить подписку", callback_data="check_subscription")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    return kb


def subscription_days_kb():
    """Клавиатура выбора количества дней"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ 1 день", callback_data="days_1")
        ],
        [
            InlineKeyboardButton(text="3️⃣ 3 дня", callback_data="days_3")
        ],
        [
            InlineKeyboardButton(text="7️⃣ 7 дней", callback_data="days_7")
        ],
        [
            InlineKeyboardButton(text="🔢 Свой период", callback_data="days_custom")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")
        ]
    ])
    return kb


@router.callback_query(F.data == "admin_subscriptions")
async def admin_subscriptions_menu(callback: types.CallbackQuery):
    """Главное меню управления подписками"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Статистика подписок
    sub_stats = await db.get_subscription_statistics()
    
    await callback.message.edit_text(
        f"📝 <b>Управление подписками</b>\n\n"
        f"📊 Статистика:\n"
        f"├ Всего: {sub_stats['total']}\n"
        f"├ Активных: {sub_stats['active']}\n"
        f"└ Истекших: {sub_stats['expired']}\n\n"
        "Выберите действие:",
        reply_markup=subscription_management_kb()
    )
    await callback.answer()


# ==================== ВЫДАТЬ ПОДПИСКУ ====================

@router.callback_query(F.data == "give_subscription")
async def give_subscription_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало выдачи подписки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ <b>Выдать подписку</b>\n\n"
        "Отправьте <b>User ID</b> пользователя:\n\n"
        "Например: <code>123456789</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")]
        ])
    )
    await state.set_state(SubscriptionManagementStates.waiting_for_user_id_give)
    await callback.answer()


@router.message(SubscriptionManagementStates.waiting_for_user_id_give)
async def process_user_id_for_give(message: types.Message, state: FSMContext):
    """Обработка User ID для выдачи подписки"""
    try:
        user_id = int(message.text)
        
        # Проверяем существование пользователя
        if not await db.user_exists(user_id):
            await message.answer(
                f"❌ <b>Пользователь не найден</b>\n\n"
                f"User ID: <code>{user_id}</code>\n\n"
                "Пользователь должен хотя бы раз запустить бота (/start)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
                ])
            )
            await state.clear()
            return
        
        # Проверяем текущую подписку
        has_sub = await db.has_subscription(user_id)
        is_active = await db.is_subscription_active(user_id)
        
        status_text = ""
        if has_sub:
            end_date = await db.get_subscription_end_date(user_id)
            if is_active:
                status_text = f"✅ Активна до: {end_date.strftime('%d.%m.%Y %H:%M')}"
            else:
                status_text = f"⌛ Истекла: {end_date.strftime('%d.%m.%Y %H:%M')}"
        else:
            status_text = "❌ Нет подписки"
        
        # Сохраняем user_id
        await state.update_data(target_user_id=user_id)
        
        # Показываем выбор дней
        await message.answer(
            f"✅ <b>Пользователь найден</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"📝 Статус: {status_text}\n\n"
            "Выберите период подписки:",
            reply_markup=subscription_days_kb()
        )
        await state.set_state(SubscriptionManagementStates.choosing_days)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "User ID должен быть числом.\n"
            "Попробуйте снова:"
        )


@router.callback_query(F.data.startswith("days_"))
async def process_days_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора количества дней"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    days_str = callback.data.replace("days_", "")
    
    # Если выбран свой период
    if days_str == "custom":
        await callback.message.edit_text(
            "🔢 <b>Свой период</b>\n\n"
            "Введите количество дней:\n\n"
            "Например: <code>30</code>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")]
            ])
        )
        await state.set_state(SubscriptionManagementStates.waiting_for_custom_days)
        await callback.answer()
        return
    
    days = int(days_str)
    await give_subscription_to_user(callback, state, days)


@router.message(SubscriptionManagementStates.waiting_for_custom_days)
async def process_custom_days(message: types.Message, state: FSMContext):
    """Обработка ввода своего количества дней"""
    try:
        days = int(message.text)
        
        if days < 1:
            await message.answer("❌ Минимум 1 день!")
            return
        
        if days > 365:
            await message.answer("❌ Максимум 365 дней!")
            return
        
        # Создаем callback для передачи в функцию
        class FakeCallback:
            def __init__(self, msg):
                self.message = msg
                self.from_user = msg.from_user
            async def answer(self):
                pass
        
        fake_cb = FakeCallback(message)
        await give_subscription_to_user(fake_cb, state, days)
        
    except ValueError:
        await message.answer("❌ Введите число дней!")


async def give_subscription_to_user(callback, state: FSMContext, days: int):
    """Выдача подписки пользователю"""
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    if not user_id:
        await callback.message.answer("❌ User ID не найден")
        await state.clear()
        return
    
    try:
        # Продлеваем подписку на указанное количество дней
        await db.extend_subscription(user_id, days)
        
        # Получаем новую дату окончания
        end_date = await db.get_subscription_end_date(user_id)
        
        await callback.message.answer(
            f"✅ <b>Подписка выдана!</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"📅 Период: {days} дн.\n"
            f"📆 Действует до: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Пользователь получил доступ к обработке видео!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Выдать еще", callback_data="give_subscription")],
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
            ])
        )
        
        await state.clear()
        
    except Exception as e:
        print(f"❌ Ошибка при выдаче подписки: {e}")
        await callback.message.answer(
            f"❌ <b>Ошибка при выдаче подписки</b>\n\n{e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
            ])
        )
        await state.clear()


# ==================== ЗАБРАТЬ ПОДПИСКУ ====================

@router.callback_query(F.data == "remove_subscription")
async def remove_subscription_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало удаления подписки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➖ <b>Забрать подписку</b>\n\n"
        "Отправьте <b>User ID</b> пользователя:\n\n"
        "Например: <code>123456789</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")]
        ])
    )
    await state.set_state(SubscriptionManagementStates.waiting_for_user_id_remove)
    await callback.answer()


@router.message(SubscriptionManagementStates.waiting_for_user_id_remove)
async def process_user_id_for_remove(message: types.Message, state: FSMContext):
    """Обработка User ID для удаления подписки"""
    try:
        user_id = int(message.text)
        
        # Проверяем существование подписки
        if not await db.has_subscription(user_id):
            await message.answer(
                f"❌ <b>У пользователя нет подписки</b>\n\n"
                f"User ID: <code>{user_id}</code>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
                ])
            )
            await state.clear()
            return
        
        # Получаем информацию о подписке
        end_date = await db.get_subscription_end_date(user_id)
        is_active = await db.is_subscription_active(user_id)
        
        # Подтверждение удаления
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, забрать", callback_data=f"confirm_remove_{user_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")
            ]
        ])
        
        status = "✅ Активна" if is_active else "⌛ Истекла"
        
        await message.answer(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"📝 Статус: {status}\n"
            f"📆 До: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Вы уверены, что хотите забрать подписку?",
            reply_markup=kb
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "User ID должен быть числом.\n"
            "Попробуйте снова:"
        )


@router.callback_query(F.data.startswith("confirm_remove_"))
async def confirm_remove_subscription(callback: types.CallbackQuery):
    """Подтверждение удаления подписки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    user_id = int(callback.data.replace("confirm_remove_", ""))
    
    try:
        # Удаляем подписку
        await db.remove_subscription(user_id)
        
        await callback.message.edit_text(
            f"✅ <b>Подписка удалена!</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n\n"
            "Пользователь больше не имеет доступа к обработке видео.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➖ Забрать еще", callback_data="remove_subscription")],
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
            ])
        )
        
    except Exception as e:
        print(f"❌ Ошибка при удалении подписки: {e}")
        await callback.message.answer(
            f"❌ <b>Ошибка при удалении подписки</b>\n\n{e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
            ])
        )
    
    await callback.answer()


# ==================== ПРОВЕРИТЬ ПОДПИСКУ ====================

@router.callback_query(F.data == "check_subscription")
async def check_subscription_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало проверки подписки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔍 <b>Проверить подписку</b>\n\n"
        "Отправьте <b>User ID</b> пользователя:\n\n"
        "Например: <code>123456789</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")]
        ])
    )
    await state.set_state(SubscriptionManagementStates.waiting_for_user_id_check)
    await callback.answer()


@router.message(SubscriptionManagementStates.waiting_for_user_id_check)
async def process_user_id_for_check(message: types.Message, state: FSMContext):
    """Проверка подписки пользователя"""
    try:
        user_id = int(message.text)
        
        # Проверяем существование пользователя
        if not await db.user_exists(user_id):
            await message.answer(
                f"❌ <b>Пользователь не найден</b>\n\n"
                f"User ID: <code>{user_id}</code>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
                ])
            )
            await state.clear()
            return
        
        # Проверяем подписку
        has_sub = await db.has_subscription(user_id)
        
        if not has_sub:
            # Кнопки для быстрой выдачи
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="give_subscription")],
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
            ])
            
            await message.answer(
                f"❌ <b>Подписки нет</b>\n\n"
                f"👤 User ID: <code>{user_id}</code>\n\n"
                "У пользователя нет подписки.",
                reply_markup=kb
            )
        else:
            end_date = await db.get_subscription_end_date(user_id)
            is_active = await db.is_subscription_active(user_id)
            
            # Вычисляем оставшееся время
            if is_active:
                remaining = end_date - datetime.now()
                days_left = remaining.days
                hours_left = remaining.seconds // 3600
                status_emoji = "✅"
                status_text = "Активна"
            else:
                status_emoji = "⌛"
                status_text = "Истекла"
                days_left = 0
                hours_left = 0
            
            # Кнопки для действий
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Продлить", callback_data="give_subscription")],
                [InlineKeyboardButton(text="➖ Забрать", callback_data="remove_subscription")],
                [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_subscriptions")]
            ])
            
            await message.answer(
                f"{status_emoji} <b>Информация о подписке</b>\n\n"
                f"👤 User ID: <code>{user_id}</code>\n"
                f"📝 Статус: {status_text}\n"
                f"📆 До: {end_date.strftime('%d.%m.%Y %H:%M')}\n"
                f"⏱ Осталось: {days_left} дн. {hours_left} ч.\n",
                reply_markup=kb
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "User ID должен быть числом.\n"
            "Попробуйте снова:"
        )

