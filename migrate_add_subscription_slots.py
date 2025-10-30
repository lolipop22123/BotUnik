#!/usr/bin/env python3
"""
Миграция для добавления таблицы subscription_slots для хранения количества доступных подписок
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Добавляет таблицу subscription_slots"""
    
    # Подключение к базе данных
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "1111"),
        database=os.getenv("POSTGRES_DB", "botUnik")
    )
    
    try:
        print("Создаем таблицу subscription_slots...")
        
        with conn.cursor() as cur:
            # Проверяем, существует ли уже таблица
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'subscription_slots'
            """)
            
            result = cur.fetchone()
            
            if result:
                print("Таблица subscription_slots уже существует")
            else:
                # Создаем таблицу subscription_slots
                cur.execute("""
                    CREATE TABLE public.subscription_slots (
                        id SERIAL PRIMARY KEY,
                        available_slots INTEGER NOT NULL DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT single_row CHECK (id = 1)
                    )
                """)
                print("Таблица subscription_slots создана")
            
            # Проверяем, есть ли уже запись с id = 1
            cur.execute("SELECT COUNT(*) FROM public.subscription_slots WHERE id = 1")
            count = cur.fetchone()[0]
            
            if count == 0:
                # Вставляем начальную запись
                cur.execute("""
                    INSERT INTO public.subscription_slots (id, available_slots)
                    VALUES (1, 0)
                """)
                print("Начальная запись добавлена (available_slots = 0)")
            else:
                print("Начальная запись уже существует")
            
            conn.commit()
            
            # Получаем текущее значение available_slots
            cur.execute("SELECT available_slots FROM public.subscription_slots WHERE id = 1")
            result = cur.fetchone()
            if result:
                current_slots = result[0]
                print(f"📊 Текущее значение available_slots в БД: {current_slots}")
            else:
                print("⚠️ Не удалось получить значение available_slots")
        
        print("Миграция завершена!")
        
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
