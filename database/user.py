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

    async def ensure_pool(self):
        """
        Гарантирует, что у нас есть живой рабочий пул.
        Если пула нет, создаёт.
        Если пул битый (коннект упал), пересоздаёт.
        """
        if self.pool is None:
            await self.connect()
            return

        # health-check
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1;")
        except Exception:
            # пул или соединение внутри него мёртвые → пересоздаём
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
    
    async def get_all_users(self) -> list:
        """Получает список всех пользователей"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT user_id, username FROM public.users ORDER BY id"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
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
    
    # async def is_subscription_active(self, user_id: int) -> bool:
    #     """
    #     Проверяет, активна ли подписка пользователя
        
    #     Args:
    #         user_id: ID пользователя
            
    #     Returns:
    #         True если подписка активна (не истекла)
    #     """
    #     if self.pool is None:
    #         await self.connect()
        
    #     query = """
    #         SELECT subscription_end_date > CURRENT_TIMESTAMP 
    #         FROM public.subscriptions 
    #         WHERE user_id = $1
    #     """
    #     async with self.pool.acquire() as conn:
    #         result = await conn.fetchval(query, user_id)
    #         return bool(result) if result is not None else False
    
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
        
        await self.ensure_pool()
            
        query = """
            SELECT 1 FROM public.subscriptions
            WHERE user_id = $1 AND subscription_end_date > CURRENT_TIMESTAMP
            LIMIT 1
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, user_id)
            return bool(result)
    
    # --- Методы для работы со шрифтами ---
    
    async def add_font(self, file_id: str, file_name: str, file_path: str, added_by: int) -> int:
        """Добавляет шрифт в базу данных"""
        if self.pool is None:
            await self.connect()
        
        query = """
            INSERT INTO public.fonts (file_id, file_name, file_path, added_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (file_id) DO UPDATE SET
                file_name = $2, file_path = $3
            RETURNING id
        """
        async with self.pool.acquire() as conn:
            font_id = await conn.fetchval(query, file_id, file_name, file_path, added_by)
            return font_id
    
    async def get_all_fonts(self) -> list:
        """Получает список всех шрифтов"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT id, file_id, file_name, file_path, created_at FROM public.fonts ORDER BY created_at DESC"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def get_font_by_id(self, font_id: int):
        """Получает шрифт по ID"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM public.fonts WHERE id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, font_id)
            return dict(row) if row else None
    
    async def delete_font(self, font_id: int) -> None:
        """Удаляет шрифт"""
        if self.pool is None:
            await self.connect()
        
        query = "DELETE FROM public.fonts WHERE id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, font_id)
    
    # --- Методы для работы с музыкой ---
    
    async def add_music(self, file_id: str, file_name: str, file_path: str, duration: int, added_by: int) -> int:
        """Добавляет музыку в базу данных"""
        if self.pool is None:
            await self.connect()
        
        query = """
            INSERT INTO public.music (file_id, file_name, file_path, duration, added_by)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (file_id) DO UPDATE SET
                file_name = $2, file_path = $3, duration = $4
            RETURNING id
        """
        async with self.pool.acquire() as conn:
            music_id = await conn.fetchval(query, file_id, file_name, file_path, duration, added_by)
            return music_id
    
    async def get_music_by_id(self, music_id: int):
        """Получает музыку по ID"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM public.music WHERE id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, music_id)
            return dict(row) if row else None
    
    async def delete_music(self, music_id: int) -> None:
        """Удаляет музыку"""
        if self.pool is None:
            await self.connect()
        
        query = "DELETE FROM public.music WHERE id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, music_id)
    
    async def get_random_music(self):
        """Получает случайную активную музыку"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM public.music WHERE is_active = true ORDER BY RANDOM() LIMIT 1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return dict(row) if row else None
    
    async def get_active_music(self):
        """Получает всю активную музыку"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM public.music WHERE is_active = true ORDER BY file_name"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def get_all_music(self):
        """Получает всю музыку (активную и неактивную)"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM public.music ORDER BY file_name"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def get_music_by_id(self, music_id: int):
        """Получает музыку по ID"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM public.music WHERE id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, music_id)
            return dict(row) if row else None
    
    async def toggle_music_status(self, music_id: int) -> bool:
        """Переключает статус музыки (активна/неактивна)"""
        if self.pool is None:
            await self.connect()
        
        query = """
            UPDATE public.music 
            SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING is_active
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, music_id)
            return bool(result) if result is not None else False
    
    async def sync_music_from_folder(self, music_folder_path: str) -> int:
        """Синхронизирует музыку из папки с базой данных"""
        if self.pool is None:
            await self.connect()
        
        import os
        from pathlib import Path
        
        music_folder = Path(music_folder_path)
        if not music_folder.exists():
            return 0
        
        added_count = 0
        
        # Поддерживаемые форматы
        supported_formats = ['.mp3', '.wav', '.m4a', '.aac', '.ogg']
        
        for file_path in music_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                file_name = file_path.name
                file_path_str = str(file_path)
                
                # Проверяем, есть ли уже такой файл
                check_query = "SELECT id FROM public.music WHERE file_path = $1"
                async with self.pool.acquire() as conn:
                    existing = await conn.fetchval(check_query, file_path_str)
                
                if not existing:
                    # Добавляем новую музыку
                    add_query = """
                        INSERT INTO public.music (file_id, file_name, file_path, duration, added_by, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        RETURNING id
                    """
                    async with self.pool.acquire() as conn:
                        music_id = await conn.fetchval(
                            add_query, 
                            f"local_{file_name}",  # Локальный ID
                            file_name, 
                            file_path_str, 
                            0,  # Длительность пока 0
                            0,  # Добавлено системой
                            True  # По умолчанию активна
                        )
                        if music_id:
                            added_count += 1
        
        return added_count
    
    async def sync_fonts_from_folder(self, fonts_folder_path: str) -> int:
        """Синхронизирует шрифты из папки с базой данных"""
        if self.pool is None:
            await self.connect()
        
        import os
        from pathlib import Path
        
        fonts_folder = Path(fonts_folder_path)
        if not fonts_folder.exists():
            return 0
        
        added_count = 0
        
        # Поддерживаемые форматы шрифтов
        supported_formats = ['.ttf', '.otf', '.woff', '.woff2']
        
        for file_path in fonts_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                file_name = file_path.name
                file_path_str = str(file_path)
                
                # Проверяем, есть ли уже такой файл
                check_query = "SELECT id FROM public.fonts WHERE file_path = $1"
                async with self.pool.acquire() as conn:
                    existing = await conn.fetchval(check_query, file_path_str)
                
                if not existing:
                    # Добавляем новый шрифт
                    add_query = """
                        INSERT INTO public.fonts (file_id, file_name, file_path, added_by)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id
                    """
                    async with self.pool.acquire() as conn:
                        font_id = await conn.fetchval(
                            add_query, 
                            f"local_{file_name}",  # Локальный ID
                            file_name, 
                            file_path_str, 
                            0  # Добавлено системой
                        )
                        if font_id:
                            added_count += 1
        
        return added_count
    
    # --- Методы для статистики ---
    
    async def count_users(self) -> int:
        """Подсчет всех пользователей"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT COUNT(*) FROM public.users"
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(query)
            return count or 0
    
    async def count_users_by_period(self, days: int, offset: int = 0) -> int:
        """Подсчет пользователей за период"""
        if self.pool is None:
            await self.connect()
        
        if days == 0:
            # За сегодня
            query = """
                SELECT COUNT(*) FROM public.users 
                WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '%s days'
            """ % offset
        else:
            # За указанный период
            query = """
                SELECT COUNT(*) FROM public.users 
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days' - INTERVAL '%s days'
                AND created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """ % (days + offset, offset, offset)
        
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(query)
            return count or 0
    
    async def get_invoice_statistics(self) -> dict:
        """Статистика по инвойсам"""
        if self.pool is None:
            await self.connect()
        
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END) as paid,
                COALESCE(SUM(amount), 0) as total_amount
            FROM public.processed_invoices
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return {
                'total': row['total'] or 0,
                'paid': row['paid'] or 0,
                'total_amount': float(row['total_amount']) if row['total_amount'] else 0.0
            }
    
    async def get_subscription_statistics(self) -> dict:
        """Статистика по подпискам"""
        if self.pool is None:
            await self.connect()
        
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN subscription_end_date > CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN subscription_end_date <= CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as expired
            FROM public.subscriptions
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return {
                'total': row['total'] or 0,
                'active': row['active'] or 0,
                'expired': row['expired'] or 0
            }
    
    async def get_amount_by_period(self, days: int, offset: int = 0) -> float:
        """Сумма платежей за период"""
        if self.pool is None:
            await self.connect()
        
        if days == 0:
            # За сегодня
            query = """
                SELECT COALESCE(SUM(amount), 0) FROM public.processed_invoices 
                WHERE DATE(processed_at) = CURRENT_DATE - INTERVAL '%s days'
            """ % offset
        else:
            # За указанный период
            query = """
                SELECT COALESCE(SUM(amount), 0) FROM public.processed_invoices 
                WHERE processed_at >= CURRENT_TIMESTAMP - INTERVAL '%s days' - INTERVAL '%s days'
                AND processed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """ % (days + offset, offset, offset)
        
        async with self.pool.acquire() as conn:
            amount = await conn.fetchval(query)
            return float(amount) if amount else 0.0
    
    async def count_invoices_by_period(self, days: int, offset: int = 0) -> int:
        """Количество платежей за период"""
        if self.pool is None:
            await self.connect()
        
        if days == 0:
            query = """
                SELECT COUNT(*) FROM public.processed_invoices 
                WHERE DATE(processed_at) = CURRENT_DATE - INTERVAL '%s days'
            """ % offset
        else:
            query = """
                SELECT COUNT(*) FROM public.processed_invoices 
                WHERE processed_at >= CURRENT_TIMESTAMP - INTERVAL '%s days' - INTERVAL '%s days'
                AND processed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """ % (days + offset, offset, offset)
        
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(query)
            return count or 0
    
    async def count_users_with_subscription(self) -> int:
        """Количество пользователей с подпиской"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT COUNT(*) FROM public.subscriptions"
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(query)
            return count or 0
    
    async def count_expiring_subscriptions(self, days: int) -> int:
        """Количество подписок истекающих в ближайшие дни"""
        if self.pool is None:
            await self.connect()
        
        if days == 0:
            query = """
                SELECT COUNT(*) FROM public.subscriptions 
                WHERE DATE(subscription_end_date) = CURRENT_DATE
            """
        else:
            query = """
                SELECT COUNT(*) FROM public.subscriptions 
                WHERE subscription_end_date BETWEEN CURRENT_TIMESTAMP 
                AND CURRENT_TIMESTAMP + INTERVAL '%s days'
            """ % days
        
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(query)
            return count or 0
    
    async def get_avg_subscription_duration(self) -> int:
        """Средняя длительность подписки в днях"""
        if self.pool is None:
            await self.connect()
        
        query = """
            SELECT AVG(EXTRACT(DAY FROM (subscription_end_date - created_at))) 
            FROM public.subscriptions
        """
        
        async with self.pool.acquire() as conn:
            avg = await conn.fetchval(query)
            return int(avg) if avg else 0
    
    async def get_free_videos_used(self, user_id: int) -> int:
        """Получить количество использованных бесплатных видео"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT free_videos_used FROM public.users WHERE user_id = $1"
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, user_id)
            return result if result is not None else 0
    
    async def increment_free_videos_used(self, user_id: int) -> None:
        """Увеличить счетчик использованных бесплатных видео"""
        if self.pool is None:
            await self.connect()
        
        query = """
            UPDATE public.users 
            SET free_videos_used = free_videos_used + 1 
            WHERE user_id = $1
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, user_id)
    
    async def can_use_free_video(self, user_id: int) -> bool:
        """Проверить, может ли пользователь использовать бесплатное видео"""
        free_used = await self.get_free_videos_used(user_id)
        return free_used < 1  # Максимум 1 бесплатное видео

# ↓↓↓ создаём один общий экземпляр и берём параметры из ENV
DBNAME = os.getenv("POSTGRES_DB", "botUnik")
DBUSER = os.getenv("POSTGRES_USER", "postgres")
DBPASS = os.getenv("POSTGRES_PASSWORD", "1111")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = int(os.getenv("POSTGRES_PORT", 5432))

db = AsyncDB(DBNAME, DBUSER, DBPASS, DBHOST, DBPORT)
