import os

from dotenv import load_dotenv


load_dotenv()

# Настройки бота конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_token_here")               # Token of your bot
ADMIN_ID = int(os.getenv("ADMIN_ID", 123456789))                    # Id of your admin

DB_URL = os.getenv("DB_URL", "your_database_url_here")              # Url of your database

RATE_LIMIT_PER_MIN: int = int(os.getenv("RATE_LIMIT_PER_MIN", 20))  # Rate limit per minute

# CryptoBot API Token
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "your_crypto_bot_token_here")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Put it into .env or environment.")











