#!/usr/bin/env python3
"""
Миграция для добавления поля free_videos_used в таблицу users
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Добавляет поле free_videos_used в таблицу users"""
    
    # Подключение к базе данных
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "botunik")
    )
    
    try:
        print("🔄 Добавляем поле free_videos_used в таблицу users...")
        
        # Проверяем, существует ли уже поле
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'free_videos_used'
        """
        
        result = await conn.fetch(check_query)
        
        if result:
            print("✅ Поле free_videos_used уже существует")
        else:
            # Добавляем поле
            alter_query = """
            ALTER TABLE users 
            ADD COLUMN free_videos_used INTEGER DEFAULT 0
            """
            
            await conn.execute(alter_query)
            print("✅ Поле free_videos_used добавлено успешно")
        
        print("🎉 Миграция завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
