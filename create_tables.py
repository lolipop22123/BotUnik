# create_tables.py
import os
import psycopg2

from dotenv import load_dotenv

load_dotenv()

DBNAME = os.getenv("POSTGRES_DB", "botUnik")
DBUSER = os.getenv("POSTGRES_USER", "postgres")
DBPASS = os.getenv("POSTGRES_PASSWORD", "1111")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = int(os.getenv("POSTGRES_PORT", 5432))

class DB:
    def __init__(self, dbname: str, user: str, password: str, host: str, port: int = 5432):
        self.connection = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            sslmode="disable",
        )
        self.connection.autocommit = True

    def create(self) -> None:
        with self.connection.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    username VARCHAR,
                    balance DOUBLE PRECISION DEFAULT 0
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_user_id
                ON public.users(user_id);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.processed_invoices (
                    id SERIAL PRIMARY KEY,
                    invoice_id BIGINT UNIQUE NOT NULL,
                    user_id BIGINT NOT NULL,
                    amount DOUBLE PRECISION NOT NULL,
                    asset VARCHAR(10) NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_invoices_invoice_id
                ON public.processed_invoices(invoice_id);
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    subscription_end_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id
                ON public.subscriptions(user_id);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date
                ON public.subscriptions(subscription_end_date);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.fonts (
                    id SERIAL PRIMARY KEY,
                    file_id VARCHAR(255) UNIQUE NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500),
                    added_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_fonts_file_id
                ON public.fonts(file_id);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.music (
                    id SERIAL PRIMARY KEY,
                    file_id VARCHAR(255) UNIQUE NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500),
                    duration INTEGER,
                    added_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_music_file_id
                ON public.music(file_id);
            """)
        print("✅ Все таблицы созданы/проверены")

    def close(self) -> None:
        try:
            self.connection.close()
        except Exception:
            pass

if __name__ == "__main__":
    db = DB(DBNAME, DBUSER, DBPASS, DBHOST, DBPORT)
    try:
        db.create()
    finally:
        db.close()
