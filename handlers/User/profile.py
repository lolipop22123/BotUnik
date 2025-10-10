import aiohttp
import asyncio

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from datetime import datetime, timedelta

from database.user import db
from keyboards.kb_user import profile_reply_kb, main_reply_kb
from handlers.User.states import PaymentStates
from config import CRYPTO_BOT_TOKEN

router = Router()

# Словарь для отслеживания активных задач проверки
active_invoice_tasks = {}


async def create_crypto_invoice(amount: float, user_id: int) -> dict:
    """
    Создает инвойс в CryptoBot API
    
    Args:
        amount: Сумма в USD
        user_id: ID пользователя Telegram
        
    Returns:
        dict с данными инвойса или None при ошибке
    """
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Параметры инвойса
    payload = {
        "asset": "USDT",  # Можно изменить на другую криптовалюту
        "amount": str(amount),
        "description": f"Пополнение баланса для пользователя {user_id}",
        "paid_btn_name": "callback",  # Кнопка после оплаты
        "paid_btn_url": f"https://t.me/YOUR_BOT_USERNAME",  # Замените на username вашего бота
        "payload": str(user_id)  # Для идентификации пользователя при webhook
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return data.get("result")
                return None
    except Exception as e:
        print(f"Ошибка при создании инвойса: {e}")
        return None


async def check_invoice_status(invoice_id: int) -> dict:
    """
    Проверяет статус инвойса в CryptoBot API
    
    Args:
        invoice_id: ID инвойса для проверки
        
    Returns:
        dict с данными инвойса или None при ошибке
        Статусы: active, paid, expired
    """
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Параметры для получения конкретного инвойса
    params = {
        "invoice_ids": str(invoice_id)
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok") and data.get("result", {}).get("items"):
                        # Возвращаем первый (и единственный) инвойс
                        return data["result"]["items"][0]
                return None
    except Exception as e:
        print(f"Ошибка при проверке статуса инвойса: {e}")
        return None


async def auto_check_invoice(bot: Bot, user_id: int, invoice_id: int, amount: float, asset: str):
    """
    Автоматически проверяет статус инвойса в фоне
    
    Args:
        bot: Экземпляр бота для отправки сообщений
        user_id: ID пользователя
        invoice_id: ID инвойса
        amount: Сумма платежа
        asset: Криптовалюта
    """
    timeout = 300  # 5 минут = 300 секунд
    check_interval = 10  # Проверять каждые 10 секунд
    elapsed_time = 0
    
    try:
        while elapsed_time < timeout:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
            
            # Проверяем статус инвойса
            invoice_data = await check_invoice_status(invoice_id)
            
            if not invoice_data:
                continue
            
            status = invoice_data.get("status")
            
            if status == "paid":
                # Проверяем, не был ли инвойс уже обработан
                if await db.is_invoice_processed(invoice_id):
                    # Уже обработан, завершаем задачу
                    break
                
                try:
                    # Помечаем инвойс как обработанный
                    await db.mark_invoice_processed(invoice_id, user_id, amount, asset)
                    
                    # Зачисляем баланс
                    new_balance = await db.add_balance(user_id, amount)
                    
                    # Отправляем уведомление пользователю
                    await bot.send_message(
                        user_id,
                        "✅ <b>Платеж успешно получен!</b>\n\n"
                        f"💰 Зачислено: {amount} {asset}\n"
                        f"💳 Новый баланс: {new_balance} $\n\n"
                        f"🆔 ID инвойса: <code>{invoice_id}</code>\n\n"
                        "Спасибо за пополнение! 🎉",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🚹 Профиль", callback_data="profile")]
                        ])
                    )
                    print(f"✅ Инвойс {invoice_id} оплачен и обработан для пользователя {user_id}")
                except Exception as e:
                    print(f"❌ Ошибка при обработке оплаченного инвойса {invoice_id}: {e}")
                    await bot.send_message(
                        user_id,
                        "⚠️ <b>Платеж получен, но возникла ошибка</b>\n\n"
                        "Обратитесь в поддержку для зачисления средств.\n\n"
                        f"🆔 ID инвойса: <code>{invoice_id}</code>",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🌐 Поддержка", url="https://t.me/makker_o")]
                        ])
                    )
                
                # Платеж обработан, завершаем задачу
                break
                
            elif status == "expired":
                # Инвойс истек
                await bot.send_message(
                    user_id,
                    "⌛ <b>Время оплаты истекло</b>\n\n"
                    f"Инвойс на сумму {amount} {asset} был отменен.\n"
                    f"🆔 ID инвойса: <code>{invoice_id}</code>\n\n"
                    "Создайте новый инвойс для пополнения баланса.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💰 Пополнить снова", callback_data="cryptobotadd")]
                    ])
                )
                print(f"⌛ Инвойс {invoice_id} истек для пользователя {user_id}")
                break
        
        # Если прошло 5 минут и платеж не получен
        if elapsed_time >= timeout:
            invoice_data = await check_invoice_status(invoice_id)
            if invoice_data and invoice_data.get("status") == "active":
                await bot.send_message(
                    user_id,
                    "❌ <b>Заказ отменен</b>\n\n"
                    f"Время ожидания оплаты истекло (5 минут).\n"
                    f"Инвойс на сумму {amount} {asset} отменен.\n\n"
                    f"🆔 ID инвойса: <code>{invoice_id}</code>\n\n"
                    "Вы можете создать новый инвойс для пополнения.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💰 Пополнить снова", callback_data="cryptobotadd")]
                    ])
                )
                print(f"❌ Инвойс {invoice_id} отменен по таймауту для пользователя {user_id}")
                
    except asyncio.CancelledError:
        print(f"🔄 Задача проверки инвойса {invoice_id} была отменена")
    except Exception as e:
        print(f"❌ Ошибка в фоновой проверке инвойса {invoice_id}: {e}")
    finally:
        # Удаляем задачу из активных
        if invoice_id in active_invoice_tasks:
            del active_invoice_tasks[invoice_id]


@router.callback_query(F.data == "profile")
async def profile_cb(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    
        user_id = callback.from_user.id
        username = callback.from_user.username
        balance = await db.get_balance(user_id)
        
        await callback.message.answer(
            f"🚹 <b>Профиль</b>\n\n"
            f"👤 <b>ID:</b> {user_id}\n"
            f"👤 <b>Имя:</b> {username}\n"
            f"💰 <b>Баланс:</b> {balance} $",
            reply_markup=profile_reply_kb()
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        pass


@router.callback_query(F.data == "balanceadd")
async def balanceadd_cb(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="CryptoBot", callback_data="cryptobotadd")
            ],
            [
                InlineKeyboardButton(text="Cryptomus", callback_data="tetheradd")
            ],
            [
                InlineKeyboardButton(text=" ⬅️", callback_data="backprofile")
            ]
        ])

        await callback.message.answer(
            f"🚹 <b>Выберите способ пополнения баланса:</b>\n\n",
            reply_markup=kb
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        pass
    
@router.callback_query(F.data == "cryptobotadd")
async def cryptobotadd_cb(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
        
        """Начало процесса пополнения через CryptoBot"""
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")
            ]
        ])
        
        await callback.message.answer(
            "💰 <b>Пополнение баланса через CryptoBot</b>\n\n"
            "Введите сумму пополнения в USD (например: 10):\n"
            "Минимальная сумма: 1 USD",
            reply_markup=kb
        )
        await state.set_state(PaymentStates.waiting_for_amount)
        await callback.answer()
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        pass


@router.message(PaymentStates.waiting_for_amount)
async def process_payment_amount(message: types.Message, state: FSMContext):
    """Обработка введенной суммы и создание инвойса"""
    try:
        amount = float(message.text)
        
        # Валидация суммы
        if amount < 1:
            await message.answer(
                "❌ Минимальная сумма пополнения: 1 USD\n"
                "Попробуйте снова:"
            )
            return
        
        if amount > 10000:
            await message.answer(
                "❌ Максимальная сумма пополнения: 10000 USD\n"
                "Попробуйте снова:"
            )
            return
        
        # Отправляем сообщение о создании инвойса
        processing_msg = await message.answer("⏳ Создаем инвойс...")
        
        # Создаем инвойс
        invoice_data = await create_crypto_invoice(amount, message.from_user.id)
        
        if invoice_data:
            # Получаем ссылку на оплату
            pay_url = invoice_data.get("pay_url") or invoice_data.get("bot_invoice_url")
            invoice_id = invoice_data.get("invoice_id")
            asset = invoice_data.get("asset", "USDT")
            
            # Создаем клавиатуру с кнопкой оплаты
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💳 Оплатить", url=pay_url)
                ]
            ])
            
            await processing_msg.delete()
            await message.answer(
                f"✅ <b>Инвойс успешно создан!</b>\n\n"
                f"💰 Сумма: {amount} {asset}\n"
                f"🆔 ID инвойса: <code>{invoice_id}</code>\n\n"
                f"🔄 <b>Автоматическая проверка включена</b>\n"
                f"⏱ Время на оплату: 5 минут\n\n"
                f"После оплаты средства будут <b>автоматически</b> зачислены на баланс.\n"
                f"Вы получите уведомление когда платеж будет подтвержден.",
                reply_markup=kb
            )
            
            # Получаем экземпляр бота из сообщения
            bot = message.bot
            
            # Запускаем фоновую задачу проверки инвойса
            task = asyncio.create_task(
                auto_check_invoice(bot, message.from_user.id, invoice_id, amount, asset)
            )
            active_invoice_tasks[invoice_id] = task
            
            print(f"🔄 Запущена автоматическая проверка инвойса {invoice_id} для пользователя {message.from_user.id}")
            
            await state.clear()
        else:
            await processing_msg.delete()
            await message.answer(
                "❌ <b>Ошибка при создании инвойса</b>\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" ⬅️ Назад", callback_data="balanceadd")]
                ])
            )
            await state.clear()
            
    except ValueError:
        await message.answer(
            "❌ Неверный формат суммы!\n"
            "Введите число (например: 10 или 25.50):"
        )


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
        
        """Отмена процесса пополнения"""
        await state.clear()
        await callback.message.answer(
            "❌ Пополнение отменено",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" ⬅️ К способам пополнения", callback_data="balanceadd")]
            ])
        )
        await callback.answer()
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        pass


@router.callback_query(F.data == "backprofile")
async def backprofile_cb(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
        user_id = callback.from_user.id
        username = callback.from_user.username
        balance = await db.get_balance(user_id)
        
        await callback.message.answer(
            f"🚹 <b>Профиль</b>\n\n"
            f"👤 <b>ID:</b> {user_id}\n"
            f"👤 <b>Имя:</b> {username}\n"
            f"💰 <b>Баланс:</b> {balance} $",
            reply_markup=profile_reply_kb()
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        pass


@router.callback_query(F.data == "backstart")
async def backstart_cb(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
        await callback.message.answer(
            f"<b>Привет! Я бот</b> 🚀\n"
            "Используй кнопки ниже или /help для списка команд.",
            reply_markup=main_reply_kb()
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        pass