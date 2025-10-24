#!/usr/bin/env python3
"""
Миграция для добавления поля is_active в таблицу music
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DBNAME = os.getenv("POSTGRES_DB", "botUnik")
DBUSER = os.getenv("POSTGRES_USER", "postgres")
DBPASS = os.getenv("POSTGRES_PASSWORD", "1111")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = int(os.getenv("POSTGRES_PORT", 5432))

def migrate():
    """Добавляет поле is_active в таблицу music"""
    try:
        connection = psycopg2.connect(
            dbname=DBNAME,
            user=DBUSER,
            password=DBPASS,
            host=DBHOST,
            port=DBPORT,
            sslmode="disable",
        )
        connection.autocommit = True
        
        with connection.cursor() as cur:
            # Проверяем, существует ли уже поле is_active
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'music' AND column_name = 'is_active'
            """)
            
            if cur.fetchone() is None:
                # Добавляем поле is_active
                cur.execute("""
                    ALTER TABLE public.music 
                    ADD COLUMN is_active BOOLEAN DEFAULT true
                """)
                print("✅ Добавлено поле is_active в таблицу music")
                
                # Добавляем поле updated_at если его нет
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'music' AND column_name = 'updated_at'
                """)
                
                if cur.fetchone() is None:
                    cur.execute("""
                        ALTER TABLE public.music 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """)
                    print("✅ Добавлено поле updated_at в таблицу music")
                
                # Обновляем все существующие записи как активные
                cur.execute("UPDATE public.music SET is_active = true WHERE is_active IS NULL")
                print("✅ Все существующие записи музыки помечены как активные")
                
            else:
                print("ℹ️ Поле is_active уже существует в таблице music")
        
        connection.close()
        print("✅ Миграция завершена успешно")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")

if __name__ == "__main__":
    migrate()
