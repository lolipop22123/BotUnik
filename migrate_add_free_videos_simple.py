#!/usr/bin/env python3
"""
Миграция для добавления поля free_videos_used в таблицу users
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Добавляет поле free_videos_used в таблицу users"""
    
    # Подключение к базе данных
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "1111"),
        database=os.getenv("POSTGRES_DB", "botUnik")
    )
    
    try:
        print("Добавляем поле free_videos_used в таблицу users...")
        
        with conn.cursor() as cur:
            # Проверяем, существует ли уже поле
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'free_videos_used'
            """)
            
            result = cur.fetchone()
            
            if result:
                print("Поле free_videos_used уже существует")
            else:
                # Добавляем поле
                cur.execute("""
                    ALTER TABLE users 
                    ADD COLUMN free_videos_used INTEGER DEFAULT 0
                """)
                print("Поле free_videos_used добавлено успешно")
            
            conn.commit()
        
        print("Миграция завершена!")
        
    except Exception as e:
        print(f"Ошибка миграции: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
