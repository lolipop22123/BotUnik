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
    
    async def add_balance(self, user_id: int, amount: float) -> float:
        """
        Добавляет сумму к балансу пользователя
        
        Args:
            user_id: ID пользователя
            amount: Сумма для добавления
            
        Returns:
            Новый баланс пользователя
        """
        if self.pool is None:
            await self.connect()
        
        query = """
            UPDATE public.users 
            SET balance = balance + $2 
            WHERE user_id = $1
            RETURNING balance
        """
        async with self.pool.acquire() as conn:
            new_balance = await conn.fetchval(query, user_id, amount)
            return float(new_balance) if new_balance is not None else 0.0
    
    async def is_invoice_processed(self, invoice_id: int) -> bool:
        """
        Проверяет, был ли инвойс уже обработан
        
        Args:
            invoice_id: ID инвойса
            
        Returns:
            True если инвойс уже был обработан
        """
        if self.pool is None:
            await self.connect()
        
        query = "SELECT 1 FROM public.processed_invoices WHERE invoice_id = $1 LIMIT 1"
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, invoice_id)
            return result is not None
    
    async def mark_invoice_processed(self, invoice_id: int, user_id: int, amount: float, asset: str) -> None:
        """
        Помечает инвойс как обработанный
        
        Args:
            invoice_id: ID инвойса
            user_id: ID пользователя
            amount: Сумма платежа
            asset: Криптовалюта
        """
        if self.pool is None:
            await self.connect()
        
        query = """
            INSERT INTO public.processed_invoices (invoice_id, user_id, amount, asset)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (invoice_id) DO NOTHING
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, invoice_id, user_id, amount, asset)
    
    # --- Методы для работы с подписками ---
    
    async def add_subscription(self, user_id: int, end_date) -> None:
        """
        Добавляет подписку пользователю
        
        Args:
            user_id: ID пользователя
            end_date: Дата окончания подписки (datetime объект)
        """
        if self.pool is None:
            await self.connect()
        
        query = """
            INSERT INTO public.subscriptions (user_id, subscription_end_date)
            VALUES ($1, $2)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                subscription_end_date = $2,
                updated_at = CURRENT_TIMESTAMP
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, end_date)
    
    async def remove_subscription(self, user_id: int) -> None:
        """
        Удаляет подписку пользователя
        
        Args:
            user_id: ID пользователя
        """
        if self.pool is None:
            await self.connect()
        
        query = "DELETE FROM public.subscriptions WHERE user_id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id)
    
    async def update_subscription_date(self, user_id: int, new_end_date) -> None:
        """
        Обновляет дату окончания подписки
        
        Args:
            user_id: ID пользователя
            new_end_date: Новая дата окончания подписки (datetime объект)
        """
        if self.pool is None:
            await self.connect()
        
        query = """
            UPDATE public.subscriptions 
            SET subscription_end_date = $2, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id, new_end_date)
    
    async def get_subscription_end_date(self, user_id: int):
        """
        Получает дату окончания подписки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            datetime объект или None если подписки нет
        """
        if self.pool is None:
            await self.connect()
        
        query = "SELECT subscription_end_date FROM public.subscriptions WHERE user_id = $1"
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, user_id)
            return result
    
    async def is_subscription_active(self, user_id: int) -> bool:
        """
        Проверяет, активна ли подписка пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если подписка активна (не истекла)
        """
        if self.pool is None:
            await self.connect()
        
        query = """
            SELECT subscription_end_date > CURRENT_TIMESTAMP 
            FROM public.subscriptions 
            WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, user_id)
            return bool(result) if result is not None else False
    
    async def extend_subscription(self, user_id: int, days: int) -> None:
        """
        Продлевает подписку на указанное количество дней
        
        Args:
            user_id: ID пользователя
            days: Количество дней для продления
        """
        if self.pool is None:
            await self.connect()
        
        # Если подписка уже есть и активна - продлеваем от текущей даты окончания
        # Если подписки нет или истекла - продлеваем от текущего момента
        query = """
            INSERT INTO public.subscriptions (user_id, subscription_end_date)
            VALUES ($1, CURRENT_TIMESTAMP + INTERVAL '%s days')
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                subscription_end_date = CASE 
                    WHEN subscriptions.subscription_end_date > CURRENT_TIMESTAMP 
                    THEN subscriptions.subscription_end_date + INTERVAL '%s days'
                    ELSE CURRENT_TIMESTAMP + INTERVAL '%s days'
                END,
                updated_at = CURRENT_TIMESTAMP
        """ % (days, days, days)
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id)

    
    async def has_subscription(self, user_id: int) -> bool:
        """
        Проверяет, есть ли у пользователя запись о подписке (неважно, активна или нет)

        Args:
            user_id: ID пользователя

        Returns:
            True если запись о подписке есть, иначе False
        """
        if self.pool is None:
            await self.connect()
        query = "SELECT 1 FROM public.subscriptions WHERE user_id = $1 LIMIT 1"
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, user_id)
            return bool(result)
    
    
    async def is_subscription_active(self, user_id: int) -> bool:
        """
        Проверяет, активна ли подписка пользователя (т.е. subscription_end_date > CURRENT_TIMESTAMP)

        Args:
            user_id: ID пользователя

        Returns:
            True если подписка активна, иначе False
        """
        if self.pool is None:
            await self.connect()
        query = """
            SELECT 1 FROM public.subscriptions
            WHERE user_id = $1 AND subscription_end_date > CURRENT_TIMESTAMP
            LIMIT 1
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, user_id)
            return bool(result)
    
      

# ↓↓↓ создаём один общий экземпляр и берём параметры из ENV
DBNAME = os.getenv("POSTGRES_DB", "botUnik")
DBUSER = os.getenv("POSTGRES_USER", "postgres")
DBPASS = os.getenv("POSTGRES_PASSWORD", "1111")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = int(os.getenv("POSTGRES_PORT", 5432))

db = AsyncDB(DBNAME, DBUSER, DBPASS, DBHOST, DBPORT)
