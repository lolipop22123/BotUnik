import asyncpg

from typing import Optional, List, Any, Dict


class AsyncDB:
    def __init__(self, dbname: str, user: str, password: str, host: str, port: int = 5432):
        """
            Параметры инициализации:
            - dbname: Название базы данных
            - user: Имя пользователя
            - password: Пароль пользователя
            - host: Адрес хоста (обычно localhost или IP)
            - port: Порт (по умолчанию 5432)
        """
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.pool: Optional[asyncpg.Pool] = None


        async def connect(self):
            """Создаём пул соединений к PostgreSQL. Вызывать один раз при старте."""
            self.pool = await asyncpg.create_pool(
            database=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
            
        async def close(self):
            """Закрываем пул соединений. Вызывать при остановке."""
            if self.pool:
                await self.pool.close()
        
        
        # Users
        async def user_exists(self, user_id: int) -> bool:
            query = "SELECT 1 FROM public.users WHERE user_id = $1 LIMIT 1"
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, user_id)
            
            return bool(row)


        async def add_user(self, user_id: int, username: Optional[str], addres: Optional[str] = None,
            captha: Optional[int] = None, code: Optional[str] = None) -> None:
            query = (
                "INSERT INTO public.users (user_id, username, balance, addres, captha, code) "
                "VALUES ($1, $2, $3, $4, $5, $6) "
                "ON CONFLICT (user_id) DO NOTHING"
            )
            
            async with self.pool.acquire() as conn:
                await conn.execute(query, user_id, username, 0.0, addres, captha, code)


        async def delete_user(self, user_id: int) -> None:
            query = "DELETE FROM public.users WHERE user_id = $1"
            
            async with self.pool.acquire() as conn:
                await conn.execute(query, user_id)