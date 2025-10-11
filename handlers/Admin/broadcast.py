from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import asyncio

from database.user import db
from handlers.Admin.states import BroadcastStates
from config import ADMIN_ID

router = Router()


def broadcast_menu_kb():
    """Меню выбора типа рассылки"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Только текст", callback_data="broadcast_text")
        ],
        [
            InlineKeyboardButton(text="🖼 Только картинка", callback_data="broadcast_photo")
        ],
        [
            InlineKeyboardButton(text="🖼📝 Картинка + текст", callback_data="broadcast_photo_text")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    return kb


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_menu(callback: types.CallbackQuery):
    """Меню рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем количество пользователей
    users_count = len(await db.get_all_users())
    
    await callback.message.edit_text(
        f"📢 <b>Рассылка сообщений</b>\n\n"
        f"👥 Всего пользователей: {users_count}\n\n"
        "Выберите тип рассылки:",
        reply_markup=broadcast_menu_kb()
    )
    await callback.answer()


# ==================== ТОЛЬКО ТЕКСТ ====================

@router.callback_query(F.data == "broadcast_text")
async def broadcast_text_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало рассылки текста"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 <b>Рассылка текста</b>\n\n"
        "Отправьте текст сообщения для рассылки:\n\n"
        "💡 Можно использовать HTML форматирование:\n"
        "• <code>&lt;b&gt;жирный&lt;/b&gt;</code>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
        "• <code>&lt;code&gt;код&lt;/code&gt;</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()


@router.message(BroadcastStates.waiting_for_text)
async def process_broadcast_text(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка текста и запуск рассылки"""
    text = message.text or message.caption
    
    if not text:
        await message.answer(
            "❌ Сообщение должно содержать текст!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
            ])
        )
        return
    
    # Подтверждение рассылки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_broadcast_text")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")
        ]
    ])
    
    await message.answer(
        f"📝 <b>Предпросмотр сообщения:</b>\n\n"
        f"{text}\n\n"
        f"Начать рассылку?",
        reply_markup=kb
    )
    
    # Сохраняем текст
    await state.update_data(broadcast_text=text)


@router.callback_query(F.data == "confirm_broadcast_text")
async def confirm_broadcast_text(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и запуск рассылки текста"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    data = await state.get_data()
    text = data.get("broadcast_text")
    
    if not text:
        await callback.answer("❌ Текст не найден", show_alert=True)
        return
    
    # Получаем всех пользователей
    users = await db.get_all_users()
    
    await callback.message.edit_text(
        f"⏳ <b>Рассылка запущена...</b>\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"📤 Отправляем сообщения..."
    )
    
    # Отправляем сообщения
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(user['user_id'], text)
            success += 1
            await asyncio.sleep(0.05)  # Задержка 50мс между сообщениями
        except Exception as e:
            failed += 1
            print(f"Ошибка отправки пользователю {user['user_id']}: {e}")
    
    # Результат
    await callback.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Статистика:\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {len(users)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Новая рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text=" ⬅️ Админ панель", callback_data="admin_panel")]
        ])
    )
    
    await state.clear()
    await callback.answer()


# ==================== ТОЛЬКО КАРТИНКА ====================

@router.callback_query(F.data == "broadcast_photo")
async def broadcast_photo_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало рассылки картинки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🖼 <b>Рассылка картинки</b>\n\n"
        "Отправьте картинку для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )
    await state.set_state(BroadcastStates.waiting_for_photo)
    await callback.answer()


@router.message(BroadcastStates.waiting_for_photo, F.photo)
async def process_broadcast_photo(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка картинки и запуск рассылки"""
    photo = message.photo[-1]  # Берем самое большое фото
    
    # Подтверждение рассылки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_broadcast_photo")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")
        ]
    ])
    
    await message.answer_photo(
        photo=photo.file_id,
        caption="🖼 <b>Предпросмотр картинки</b>\n\nНачать рассылку?",
        reply_markup=kb
    )
    
    # Сохраняем file_id фото
    await state.update_data(broadcast_photo=photo.file_id)


@router.callback_query(F.data == "confirm_broadcast_photo")
async def confirm_broadcast_photo(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и запуск рассылки фото"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    data = await state.get_data()
    photo_id = data.get("broadcast_photo")
    
    if not photo_id:
        await callback.answer("❌ Фото не найдено", show_alert=True)
        return
    
    # Получаем всех пользователей
    users = await db.get_all_users()
    
    await callback.message.answer(
        f"⏳ <b>Рассылка запущена...</b>\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"📤 Отправляем картинки..."
    )
    
    # Отправляем фото
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_photo(user['user_id'], photo_id)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            print(f"Ошибка отправки пользователю {user['user_id']}: {e}")
    
    # Результат
    await callback.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Статистика:\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {len(users)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Новая рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text=" ⬅️ Админ панель", callback_data="admin_panel")]
        ])
    )
    
    await state.clear()
    await callback.answer()


# ==================== КАРТИНКА + ТЕКСТ ====================

@router.callback_query(F.data == "broadcast_photo_text")
async def broadcast_photo_text_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало рассылки картинки с текстом"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🖼📝 <b>Рассылка картинки с текстом</b>\n\n"
        "Сначала отправьте картинку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )
    await state.set_state(BroadcastStates.waiting_for_photo_with_text)
    await callback.answer()


@router.message(BroadcastStates.waiting_for_photo_with_text, F.photo)
async def process_photo_for_text(message: types.Message, state: FSMContext):
    """Получение фото, запрос текста"""
    photo = message.photo[-1]
    
    # Сохраняем file_id фото
    await state.update_data(broadcast_photo=photo.file_id)
    
    await message.answer(
        "✅ Картинка получена!\n\n"
        "📝 Теперь отправьте текст для картинки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )
    await state.set_state(BroadcastStates.waiting_for_text_with_photo)


@router.message(BroadcastStates.waiting_for_text_with_photo)
async def process_text_for_photo(message: types.Message, state: FSMContext, bot: Bot):
    """Получение текста и предпросмотр"""
    text = message.text or message.caption
    
    if not text:
        await message.answer("❌ Нужно отправить текст!")
        return
    
    data = await state.get_data()
    photo_id = data.get("broadcast_photo")
    
    # Сохраняем текст
    await state.update_data(broadcast_text=text)
    
    # Подтверждение
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_broadcast_photo_text")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")
        ]
    ])
    
    await message.answer_photo(
        photo=photo_id,
        caption=f"{text}\n\n<b>Начать рассылку?</b>",
        reply_markup=kb
    )


@router.callback_query(F.data == "confirm_broadcast_photo_text")
async def confirm_broadcast_photo_text(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и запуск рассылки фото с текстом"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    data = await state.get_data()
    photo_id = data.get("broadcast_photo")
    text = data.get("broadcast_text")
    
    if not photo_id or not text:
        await callback.answer("❌ Данные не найдены", show_alert=True)
        return
    
    # Получаем всех пользователей
    users = await db.get_all_users()
    
    await callback.message.answer(
        f"⏳ <b>Рассылка запущена...</b>\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"📤 Отправляем сообщения..."
    )
    
    # Отправляем фото с текстом
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_photo(user['user_id'], photo_id, caption=text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            print(f"Ошибка отправки пользователю {user['user_id']}: {e}")
    
    # Результат
    await callback.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Статистика:\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {len(users)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Новая рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text=" ⬅️ Админ панель", callback_data="admin_panel")]
        ])
    )
    
    await state.clear()
    await callback.answer()


@router.message(BroadcastStates.waiting_for_photo)
@router.message(BroadcastStates.waiting_for_photo_with_text)
async def invalid_photo_format(message: types.Message):
    """Обработка неверного формата"""
    await message.answer(
        "❌ Нужно отправить картинку!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )

