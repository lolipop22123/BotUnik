import os
import psycopg2


DBNAME = os.getenv("POSTGRES_DB", "cryptobot2")
DBUSER = os.getenv("POSTGRES_USER", "postgres")
DBPASS = os.getenv("POSTGRES_PASSWORD", "1111")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = int(os.getenv("POSTGRES_PORT", 5432))


class DB:
    def __init__(self, dbname, user, password, host, port=5432):
        self.connection = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
        sslmode='disable',
    )
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()

        # Users table
        def create(self):
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS public.users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE,
                username VARCHAR,
                balance DOUBLE PRECISION DEFAULT 0,
                addres VARCHAR,
                captha BIGINT,
                code VARCHAR
            );
        ''')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON public.users(user_id);')
    


if __name__ == '__main__':
    DB(DBNAME, DBUSER, DBPASS, DBHOST, DBPORT).create()