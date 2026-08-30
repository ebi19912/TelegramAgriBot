"""
Database persistence layer for TelegramAgriBot using SQLite.
Stores AI configuration, quota counters, user profiles, and chat memory.
"""

import sqlite3
import datetime
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Generator
from config import (
    DATABASE_PATH,
    DEFAULT_PROVIDER_NAME,
    DEFAULT_MODEL_NAME,
    DEFAULT_API_URL,
    DEFAULT_API_KEY,
    ENABLE_ADVANCED_REASONING,
    DEFAULT_MAX_REQUESTS,
)


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Create and yield a database connection with row factory, ensuring it is closed."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema and insert default settings if not exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. AI Settings Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    provider_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    api_url TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    reasoning_enabled INTEGER NOT NULL DEFAULT 0,
                    max_requests INTEGER NOT NULL DEFAULT 50,
                    requests_used INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # 2. Users Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    total_requests INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # 3. Chat History Table (Context memory)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Insert default row if empty
            cursor.execute("SELECT id FROM ai_settings WHERE id = 1")
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    """
                    INSERT INTO ai_settings (
                        id, provider_name, model_name, api_url, api_key,
                        reasoning_enabled, max_requests, requests_used, updated_at
                    ) VALUES (1, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                    """,
                    (
                        DEFAULT_PROVIDER_NAME,
                        DEFAULT_MODEL_NAME,
                        DEFAULT_API_URL,
                        DEFAULT_API_KEY,
                        1 if ENABLE_ADVANCED_REASONING else 0,
                        DEFAULT_MAX_REQUESTS,
                    ),
                )
            conn.commit()

    # =========================================================================
    # AI Settings & Quotas
    # =========================================================================

    def get_ai_settings(self) -> Dict[str, Any]:
        """Fetch current AI provider and model settings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_settings WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {
                "provider_name": DEFAULT_PROVIDER_NAME,
                "model_name": DEFAULT_MODEL_NAME,
                "api_url": DEFAULT_API_URL,
                "api_key": DEFAULT_API_KEY,
                "reasoning_enabled": 1 if ENABLE_ADVANCED_REASONING else 0,
                "max_requests": DEFAULT_MAX_REQUESTS,
                "requests_used": 0,
            }

    def update_ai_setting(self, field: str, value: Any) -> bool:
        """Update a specific field in the AI settings table."""
        allowed_fields = {
            "provider_name",
            "model_name",
            "api_url",
            "api_key",
            "reasoning_enabled",
            "max_requests",
            "requests_used",
        }
        if field not in allowed_fields:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE ai_settings SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
            cursor.execute(query, (value,))
            conn.commit()
            return cursor.rowcount > 0

    def increment_requests_used(self, user_id: Optional[int] = None) -> int:
        """Increment both the global request counter and user specific request count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ai_settings SET requests_used = requests_used + 1, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
            )
            if user_id:
                cursor.execute(
                    "UPDATE users SET total_requests = total_requests + 1, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,),
                )
            conn.commit()
            cursor.execute("SELECT requests_used FROM ai_settings WHERE id = 1")
            row = cursor.fetchone()
            return row["requests_used"] if row else 0

    def reset_quota(self) -> bool:
        """Reset the used requests counter back to 0."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ai_settings SET requests_used = 0, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
            )
            conn.commit()
            return True

    # =========================================================================
    # User Management
    # =========================================================================

    def register_or_update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> None:
        """Register a new user or update an existing user's last_active and name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name, total_requests, created_at, last_active)
                VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_active = CURRENT_TIMESTAMP
                """,
                (user_id, username or "", first_name or "", last_name or ""),
            )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics for admin reporting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()["total_users"]

            cursor.execute("SELECT SUM(total_requests) as sum_requests FROM users")
            sum_user_reqs = cursor.fetchone()["sum_requests"] or 0

            ai_settings = self.get_ai_settings()

            return {
                "total_users": total_users,
                "total_user_requests": sum_user_reqs,
                "requests_used": ai_settings.get("requests_used", 0),
                "max_requests": ai_settings.get("max_requests", 50),
                "provider_name": ai_settings.get("provider_name", "OpenRouter"),
                "model_name": ai_settings.get("model_name", "openrouter/free"),
                "reasoning_enabled": bool(ai_settings.get("reasoning_enabled", 0)),
            }

    # =========================================================================
    # Chat Memory / Conversation History
    # =========================================================================

    def add_chat_message(self, user_id: int, role: str, content: str) -> None:
        """Add a message to the user's chat context memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content),
            )
            conn.commit()

    def get_chat_history(self, user_id: int, limit: int = 6) -> List[Dict[str, str]]:
        """Retrieve recent chat history for context injection."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            # Reverse so it's in chronological order
            history = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
            return history

    def clear_chat_history(self, user_id: int) -> int:
        """Clear chat history for a specific user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount


# Global database instance
db = Database()
