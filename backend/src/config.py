import os

# Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "your_redis_host")

# DB
DB_HOST = os.environ.get("DB_HOST", "your_db_host")
DB_NAME = os.environ.get("POSTGRES_DB", "your_db_name")
DB_USER = os.environ.get("POSTGRES_USER", "your_db_user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "your_db_password")

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your_gemini_api_key")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "your_telegram_bot_token")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "your_telegram_chat_id")
