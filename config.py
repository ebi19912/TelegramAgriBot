"""
Configuration module for TelegramAgriBot.
Loads environment variables and sets initial default values.
"""

import os
from typing import Set
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Admin IDs
def _parse_admin_ids(raw_admin_ids: str) -> Set[int]:
    """Parse comma-separated Telegram User IDs into a set of integers."""
    ids = set()
    if not raw_admin_ids:
        return ids
    for part in raw_admin_ids.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids

ADMIN_IDS: Set[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

# Default AI Configuration Fallbacks
DEFAULT_PROVIDER_NAME: str = os.getenv("DEFAULT_PROVIDER_NAME", "OpenRouter").strip()
DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "openrouter/free").strip()
DEFAULT_API_URL: str = os.getenv(
    "DEFAULT_API_URL", "https://openrouter.ai/api/v1/chat/completions"
).strip()
DEFAULT_API_KEY: str = os.getenv("DEFAULT_API_KEY", "").strip()

# Advanced Reasoning Default
ENABLE_ADVANCED_REASONING: bool = (
    os.getenv("ENABLE_ADVANCED_REASONING", "false").lower() in ("true", "1", "yes")
)

# Quota and Limits Default (0 = unlimited)
DEFAULT_MAX_REQUESTS: int = int(os.getenv("DEFAULT_MAX_REQUESTS", "50"))

# Database path
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "agribot.db").strip()


def is_admin(user_id: int) -> bool:
    """Check if a given user_id is in the authorized admin set."""
    return user_id in ADMIN_IDS
