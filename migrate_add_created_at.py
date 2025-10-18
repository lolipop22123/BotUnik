# migrate_add_created_at.py
"""
Миграция для добавления колонки created_at в таблицу users
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
    """Добавляет колонку created_at в таблицу users"""
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
            # Добавляем колонку created_at если её нет
            cur.execute("""
                ALTER TABLE public.users 
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            
            # Обновляем существующие записи (если created_at NULL, ставим текущую дату)
            cur.execute("""
                UPDATE public.users 
                SET created_at = CURRENT_TIMESTAMP 
                WHERE created_at IS NULL;
            """)
            
            print("OK: Миграция выполнена успешно!")
            print("   Колонка created_at добавлена в таблицу users")
        
        connection.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    print("Запуск миграции...")
    migrate()
    print("Готово!")

