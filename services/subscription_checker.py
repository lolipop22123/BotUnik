import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from database.user import db
from config import BOT_TOKEN
import logging

logger = logging.getLogger(__name__)

class SubscriptionChecker:
    """Класс для проверки истечения подписок"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.is_running = False
    
    async def start_checking(self):
        """Запуск фоновой проверки подписок"""
        if self.is_running:
            logger.warning("Subscription checker уже запущен")
            return
        
        self.is_running = True
        logger.info("🔄 Запуск фоновой проверки подписок")
        
        while self.is_running:
            try:
                await self.check_expired_subscriptions()
                # Проверяем каждые 5 минут
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой проверке подписок: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    async def stop_checking(self):
        """Остановка фоновой проверки"""
        self.is_running = False
        logger.info("⏹️ Остановка фоновой проверки подписок")
    
    async def check_expired_subscriptions(self):
        """Проверка истечения подписок"""
        try:
            # Получаем всех пользователей с активными подписками
            expired_users = await self.get_expired_subscriptions()
            
            if not expired_users:
                logger.debug("✅ Нет истекших подписок")
                return
            
            logger.info(f"🔍 Найдено {len(expired_users)} истекших подписок")
            
            for user_id in expired_users:
                try:
                    # Отправляем уведомление пользователю
                    await self.send_expiration_notification(user_id)
                    
                    # Удаляем подписку из базы
                    await db.remove_subscription(user_id)
                    
                    logger.info(f"✅ Подписка пользователя {user_id} истекла и удалена")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при обработке пользователя {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке подписок: {e}")
    
    async def get_expired_subscriptions(self):
        """Получение списка пользователей с истекшими подписками"""
        try:
            if db.pool is None:
                await db.connect()
            
            query = """
                SELECT user_id 
                FROM subscriptions 
                WHERE subscription_end_date <= NOW()
            """
            
            async with db.pool.acquire() as conn:
                result = await conn.fetch(query)
                return [row['user_id'] for row in result]
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении истекших подписок: {e}")
            return []
    
    async def send_expiration_notification(self, user_id: int):
        """Отправка уведомления об истечении подписки"""
        try:
            message_text = (
                "⏰ <b>Подписка истекла</b>\n\n"
                "Ваша подписка закончилась.\n"
                "Для продолжения использования неограниченной обработки видео:\n\n"
                "• Купите новую подписку\n"
                "• Или пополните баланс для разовой обработки\n\n"
                "💡 Используйте /start для доступа к функциям бота"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode="HTML"
            )
            
            logger.info(f"📤 Уведомление об истечении подписки отправлено пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке уведомления пользователю {user_id}: {e}")
    
    async def check_subscription_status(self, user_id: int):
        """Проверка статуса подписки конкретного пользователя"""
        try:
            is_active = await db.is_subscription_active(user_id)
            if not is_active:
                return False
            
            end_date = await db.get_subscription_end_date(user_id)
            if end_date and end_date <= datetime.now():
                # Подписка истекла
                await db.remove_subscription(user_id)
                await self.send_expiration_notification(user_id)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке статуса подписки пользователя {user_id}: {e}")
            return False

# Глобальный экземпляр
subscription_checker = SubscriptionChecker()

async def start_subscription_checker():
    """Запуск фоновой проверки подписок"""
    await subscription_checker.start_checking()

async def stop_subscription_checker():
    """Остановка фоновой проверки подписок"""
    await subscription_checker.stop_checking()
