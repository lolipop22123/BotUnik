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
        print("✅ Таблица users создана/проверена")

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
