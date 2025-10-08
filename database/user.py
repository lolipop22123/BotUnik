# database/user.py
import os
import asyncpg
from typing import Optional, List

class AsyncDB:
    def __init__(self, dbname: str, user: str, password: str, host: str, port: int = 5432):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            database=self.dbname, user=self.user, password=self.password,
            host=self.host, port=self.port,
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def _ensure_pool(self):
        if self.pool is None:
            await self.connect()
            
    # --- методы ---
    async def user_exists(self, user_id: int) -> bool:
        query = "SELECT 1 FROM public.users WHERE user_id = $1 LIMIT 1"
        async with self.pool.acquire() as conn:
            return bool(await conn.fetchrow(query, user_id))

    async def add_user(self, user_id: int, username: Optional[str]) -> None:
        if self.pool is None:
            raise RuntimeError("DB pool is not initialized. Call connect() first.")
        query = """
            INSERT INTO public.users (user_id, username, balance)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, username, 0.0)

    async def delete_user(self, user_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM public.users WHERE user_id = $1", user_id)
    
    async def get_balance(self, user_id: int) -> float:
        # Подстраховка: если забыли вызвать connect()
        if self.pool is None:
            await self.connect()

        query = "SELECT balance FROM public.users WHERE user_id = $1"
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(query, user_id)
            return float(val) if val is not None else 0.0


# ↓↓↓ создаём один общий экземпляр и берём параметры из ENV
DBNAME = os.getenv("POSTGRES_DB", "botUnik")
DBUSER = os.getenv("POSTGRES_USER", "postgres")
DBPASS = os.getenv("POSTGRES_PASSWORD", "1111")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = int(os.getenv("POSTGRES_PORT", 5432))

db = AsyncDB(DBNAME, DBUSER, DBPASS, DBHOST, DBPORT)
