"""
Тестовый скрипт для проверки работы фоновой проверки подписок
"""
import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.subscription_checker import subscription_checker
from database.user import db
from datetime import datetime, timedelta

async def test_subscription_checker():
    """Тестирование сервиса проверки подписок"""
    print("🧪 Тестирование сервиса проверки подписок...")
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        print("✅ Подключение к базе данных успешно")
        
        # Тестируем получение истекших подписок
        expired_users = await subscription_checker.get_expired_subscriptions()
        print(f"📊 Найдено истекших подписок: {len(expired_users)}")
        
        if expired_users:
            print(f"👥 Пользователи с истекшими подписками: {expired_users}")
        
        # Тестируем проверку статуса подписки для конкретного пользователя
        test_user_id = 123456789  # Замените на реальный ID
        status = await subscription_checker.check_subscription_status(test_user_id)
        print(f"🔍 Статус подписки пользователя {test_user_id}: {'Активна' if status else 'Неактивна'}")
        
        print("✅ Тестирование завершено успешно")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_subscription_checker())
