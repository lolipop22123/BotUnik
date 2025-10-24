import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "1111"),
        database=os.getenv("POSTGRES_DB", "botUnik")
    )

    try:
        print("Добавляем поле is_active в таблицу music...")

        with conn.cursor() as cur:
            # Проверяем, существует ли уже поле
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='music' AND column_name='is_active';
            """)

            result = cur.fetchone()

            if result:
                print("Поле is_active уже существует")
            else:
                # Добавляем поле
                cur.execute("""
                    ALTER TABLE music
                    ADD COLUMN is_active BOOLEAN DEFAULT true
                """)
                print("Поле is_active добавлено успешно")

            # Также добавляем updated_at если его нет
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='music' AND column_name='updated_at';
            """)

            result = cur.fetchone()

            if result:
                print("Поле updated_at уже существует")
            else:
                # Добавляем поле
                cur.execute("""
                    ALTER TABLE music
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                print("Поле updated_at добавлено успешно")

            conn.commit()

        print("Миграция завершена!")

    except Exception as e:
        print(f"Ошибка миграции: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

