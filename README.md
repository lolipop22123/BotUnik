# 🤖 Шаблон Telegram Бота на Aiogram 3

Готовый шаблон для быстрого старта разработки Telegram-ботов на базе **Aiogram 3** с поддержкой базы данных PostgreSQL.

## 📋 Описание

Это базовый шаблон бота с предустановленной архитектурой, который включает в себя:
- ✅ Структурированную организацию кода
- ✅ Систему middleware (логирование, антифлуд, админ-доступ)
- ✅ Работу с базой данных PostgreSQL (синхронная и асинхронная)
- ✅ Базовые обработчики команд
- ✅ Систему конфигурации через .env файл

## 🚀 Быстрый старт

### Требования
- Python 3.10+
- PostgreSQL 12+

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone <your-repo-url>
cd <project-folder>
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Создайте файл `.env` в корне проекта:**
```env
BOT_TOKEN=ваш_токен_бота
ADMIN_ID=ваш_telegram_id
DB_URL=postgresql://user:password@localhost:5432/dbname
RATE_LIMIT_PER_MIN=20

# Для create_tables.py
POSTGRES_DB=cryptobot2
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1111
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

4. **Создайте таблицы в базе данных:**
```bash
python create_tables.py
```

5. **Запустите бота:**
```bash
python run.py
```

## 📁 Структура проекта

```
├── config.py                 # Конфигурация бота (токены, настройки)
├── run.py                    # Точка входа в приложение
├── create_tables.py          # Скрипт для создания таблиц БД
├── requirements.txt          # Зависимости проекта
│
├── handlers/                 # Обработчики команд и сообщений
│   ├── start.py             # Команда /start
│   ├── help.py              # Команда /help
│   ├── echo.py              # Echo handler (повтор сообщений)
│   ├── messages.py          # Дополнительные обработчики сообщений
│   └── errors.py            # Обработчики ошибок
│
├── middlewares/              # Промежуточные обработчики (middleware)
│   ├── logging.py           # Логирование всех сообщений
│   ├── throttling.py        # Защита от флуда (rate limiting)
│   └── admin_gate.py        # Ограничение доступа для админов
│
├── database/                 # Работа с базой данных
│   └── user.py              # Асинхронная работа с пользователями
│
├── services/                 # Вспомогательные сервисы
│   ├── commands.py          # Настройка команд бота в меню
│   └── utils.py             # Утилиты
│
├── keyboards/                # Клавиатуры для бота
│   └── kb.py                # Реализация клавиатур
│
└── logs/                     # Логи бота
    └── bot.log              # Файл логов
```

## ⚙️ Основные компоненты

### 🎯 Handlers (Обработчики)

#### `handlers/start.py`
Обрабатывает команду `/start` - приветствие при запуске бота.

#### `handlers/help.py`
Обрабатывает команду `/help` - выводит список доступных команд.

#### `handlers/echo.py`
Эхо-обработчик - повторяет все текстовые сообщения пользователя.

### 🛡️ Middlewares (Промежуточные обработчики)

#### `middlewares/logging.py` - LoggingMiddleware
Логирует все входящие сообщения с информацией о пользователе:
- ID пользователя
- Username
- Полное имя
- Текст сообщения

#### `middlewares/throttling.py` - ThrottlingMiddleware
Защита от флуда. По умолчанию ограничение - 20 сообщений в минуту на одного пользователя.
При превышении лимита пользователь получит уведомление.

#### `middlewares/admin_gate.py` - AdminGateMiddleware
Ограничивает доступ к определенным командам только для администратора.
Применяется к специальному `admin_router` для защиты админских команд.

### 💾 База данных

#### `database/user.py` - AsyncDB
Асинхронная работа с PostgreSQL через `asyncpg`:

**Методы:**
- `connect()` - создание пула соединений
- `close()` - закрытие пула
- `user_exists(user_id)` - проверка существования пользователя
- `add_user(user_id, username, ...)` - добавление нового пользователя
- `delete_user(user_id)` - удаление пользователя

**Структура таблицы `users`:**
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT UNIQUE) 
- username (VARCHAR)
- balance (DOUBLE PRECISION)
- addres (VARCHAR)
- captha (BIGINT)
- code (VARCHAR)
```

#### `create_tables.py` - DB
Синхронная работа с БД через `psycopg2` для создания таблиц.
Запустите `python create_tables.py` для инициализации БД.

### 🔧 Конфигурация

#### `config.py`
Загружает настройки из `.env` файла:
- `BOT_TOKEN` - токен бота от BotFather
- `ADMIN_ID` - Telegram ID администратора
- `DB_URL` - URL подключения к PostgreSQL
- `RATE_LIMIT_PER_MIN` - лимит сообщений в минуту (по умолчанию 20)

### 📱 Services

#### `services/commands.py`
Настраивает отображение команд в меню Telegram:
- `/start` - Запуск бота
- `/help` - Помощь
- `/admin_ping` - Проверка админа (только для администратора)

## 🔐 Админские команды

Бот включает отдельный роутер для админских команд с защитой через `AdminGateMiddleware`.

**Пример:** `/admin_ping` - доступна только пользователю с ADMIN_ID

## 📝 Как добавить новый обработчик

1. Создайте файл в папке `handlers/`, например `my_handler.py`:

```python
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("mycommand"))
async def my_command(message: types.Message):
    await message.answer("Моя команда работает!")
```

2. Подключите роутер в `run.py`:

```python
from handlers import my_handler

# В функции main():
dp.include_router(my_handler.router)
```

3. (Опционально) Добавьте команду в меню в `services/commands.py`:

```python
BotCommand(command="mycommand", description="Описание команды")
```

## 🛠️ Технологии

- **[Aiogram 3.x](https://docs.aiogram.dev/)** - асинхронный фреймворк для Telegram Bot API
- **[asyncpg](https://github.com/MagicStack/asyncpg)** - асинхронный драйвер PostgreSQL
- **[psycopg2](https://www.psycopg.org/)** - синхронный драйвер PostgreSQL
- **[SQLAlchemy 2.x](https://www.sqlalchemy.org/)** - ORM (опционально)
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - работа с .env файлами
- **[loguru](https://github.com/Delgan/loguru)** - удобное логирование

## 📌 Зависимости

```
aiogram==3.*
python-dotenv
loguru
SQLAlchemy[asyncio]==2.*
asyncpg
```

## 🎨 Дополнительные возможности для разработки

### Добавление клавиатур
Используйте файл `keyboards/kb.py` для создания кастомных клавиатур:

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Кнопка 1"), KeyboardButton(text="Кнопка 2")],
        ],
        resize_keyboard=True
    )
    return kb
```

### Работа с базой данных
Пример использования AsyncDB:

```python
from database.user import AsyncDB
import os

db = AsyncDB(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=int(os.getenv("POSTGRES_PORT", 5432))
)

# В async функции:
await db.connect()
exists = await db.user_exists(123456789)
await db.add_user(123456789, "username")
await db.close()
```

## ⚠️ Важные замечания

1. **Безопасность:** Не коммитьте `.env` файл в Git! Добавьте его в `.gitignore`.
2. **Токен бота:** Получите токен у [@BotFather](https://t.me/BotFather) в Telegram.
3. **ADMIN_ID:** Узнайте свой ID через [@userinfobot](https://t.me/userinfobot).
4. **База данных:** Убедитесь, что PostgreSQL запущен и доступен.

## 📄 Лицензия

Этот шаблон предоставляется "как есть" для свободного использования в ваших проектах.

## 🤝 Разработка

Этот шаблон создан для ускорения разработки Telegram-ботов. Вы можете:
- Добавлять новые обработчики
- Расширять функционал middleware
- Создавать собственные клавиатуры
- Добавлять новые таблицы в БД
- Интегрировать дополнительные сервисы

## 📞 Поддержка

Если у вас возникли вопросы или проблемы:
1. Проверьте правильность настроек в `.env`
2. Убедитесь, что все зависимости установлены
3. Проверьте логи в `logs/bot.log`

---

**Успешной разработки! 🚀**

