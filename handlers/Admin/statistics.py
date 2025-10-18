from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from database.user import db
from config import ADMIN_ID

router = Router()


@router.callback_query(F.data == "admin_statistics")
async def admin_statistics(callback: types.CallbackQuery):
    """Показ статистики бота"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем статистику
    stats = await get_bot_statistics()
    
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        
        "👥 <b>Пользователи:</b>\n"
        f"├ Всего: {stats['total_users']}\n"
        f"├ За сегодня: {stats['users_today']}\n"
        f"├ За неделю: {stats['users_week']}\n"
        f"└ За месяц: {stats['users_month']}\n\n"
        
        "💰 <b>Финансы:</b>\n"
        f"├ Всего платежей: {stats['total_invoices']}\n"
        f"├ Оплачено: {stats['paid_invoices']}\n"
        f"└ Сумма: {stats['total_amount']:.2f} $\n\n"
        
        "📝 <b>Подписки:</b>\n"
        f"├ Всего подписок: {stats['total_subscriptions']}\n"
        f"├ Активных: {stats['active_subscriptions']}\n"
        f"└ Истекших: {stats['expired_subscriptions']}\n\n"
        
        "🎬 <b>Медиа:</b>\n"
        f"├ Шрифтов: {stats['total_fonts']}\n"
        f"└ Музыки: {stats['total_music']}\n\n"
        
        f"🕐 <b>Обновлено:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_statistics")
        ],
        [
            InlineKeyboardButton(text="📈 Детальная статистика", callback_data="admin_statistics_detailed")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_panel")
        ]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        # Игнорируем ошибку если сообщение не изменилось
        pass
    await callback.answer("✅ Обновлено")


@router.callback_query(F.data == "admin_statistics_detailed")
async def admin_statistics_detailed(callback: types.CallbackQuery):
    """Детальная статистика"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем детальную статистику
    stats = await get_detailed_statistics()
    
    text = (
        "📈 <b>Детальная статистика</b>\n\n"
        
        "💵 <b>Финансы по дням:</b>\n"
        f"├ Сегодня: {stats['amount_today']:.2f} $\n"
        f"├ Вчера: {stats['amount_yesterday']:.2f} $\n"
        f"├ За неделю: {stats['amount_week']:.2f} $\n"
        f"└ За месяц: {stats['amount_month']:.2f} $\n\n"
        
        "📊 <b>Платежи по дням:</b>\n"
        f"├ Сегодня: {stats['invoices_today']}\n"
        f"├ Вчера: {stats['invoices_yesterday']}\n"
        f"├ За неделю: {stats['invoices_week']}\n"
        f"└ За месяц: {stats['invoices_month']}\n\n"
        
        "👤 <b>Активность пользователей:</b>\n"
        f"├ Новых сегодня: {stats['users_today']}\n"
        f"├ Новых вчера: {stats['users_yesterday']}\n"
        f"├ С подпиской: {stats['users_with_subscription']}\n"
        f"└ Без подписки: {stats['users_without_subscription']}\n\n"
        
        "📝 <b>Подписки:</b>\n"
        f"├ Истекает сегодня: {stats['expiring_today']}\n"
        f"├ Истекает за неделю: {stats['expiring_week']}\n"
        f"└ Средняя длительность: {stats['avg_subscription_days']} дней\n\n"
        
        f"🕐 <b>Обновлено:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_statistics_detailed")
        ],
        [
            InlineKeyboardButton(text=" ⬅️ Назад", callback_data="admin_statistics")
        ]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        # Игнорируем ошибку если сообщение не изменилось
        pass
    await callback.answer("✅ Обновлено")


async def get_bot_statistics() -> dict:
    """Получает основную статистику бота"""
    stats = {}
    
    # Пользователи
    stats['total_users'] = await db.count_users()
    stats['users_today'] = await db.count_users_by_period(days=0)
    stats['users_week'] = await db.count_users_by_period(days=7)
    stats['users_month'] = await db.count_users_by_period(days=30)
    
    # Платежи
    invoice_stats = await db.get_invoice_statistics()
    stats['total_invoices'] = invoice_stats['total']
    stats['paid_invoices'] = invoice_stats['paid']
    stats['total_amount'] = invoice_stats['total_amount']
    
    # Подписки
    subscription_stats = await db.get_subscription_statistics()
    stats['total_subscriptions'] = subscription_stats['total']
    stats['active_subscriptions'] = subscription_stats['active']
    stats['expired_subscriptions'] = subscription_stats['expired']
    
    # Медиа
    stats['total_fonts'] = len(await db.get_all_fonts())
    stats['total_music'] = len(await db.get_all_music())
    
    return stats


async def get_detailed_statistics() -> dict:
    """Получает детальную статистику"""
    stats = {}
    
    # Финансы по дням
    stats['amount_today'] = await db.get_amount_by_period(days=0)
    stats['amount_yesterday'] = await db.get_amount_by_period(days=1, offset=1)
    stats['amount_week'] = await db.get_amount_by_period(days=7)
    stats['amount_month'] = await db.get_amount_by_period(days=30)
    
    # Платежи по дням
    stats['invoices_today'] = await db.count_invoices_by_period(days=0)
    stats['invoices_yesterday'] = await db.count_invoices_by_period(days=1, offset=1)
    stats['invoices_week'] = await db.count_invoices_by_period(days=7)
    stats['invoices_month'] = await db.count_invoices_by_period(days=30)
    
    # Пользователи
    stats['users_today'] = await db.count_users_by_period(days=0)
    stats['users_yesterday'] = await db.count_users_by_period(days=1, offset=1)
    stats['users_with_subscription'] = await db.count_users_with_subscription()
    stats['users_without_subscription'] = await db.count_users() - stats['users_with_subscription']
    
    # Подписки истекают
    stats['expiring_today'] = await db.count_expiring_subscriptions(days=0)
    stats['expiring_week'] = await db.count_expiring_subscriptions(days=7)
    stats['avg_subscription_days'] = await db.get_avg_subscription_duration()
    
    return stats

