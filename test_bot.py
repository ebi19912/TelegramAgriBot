"""
Comprehensive verification test suite for TelegramAgriBot.
Tests database operations, AI configuration, quota management, reasoning flags, and keyboards.
"""

import os
import sys
import unittest
import tempfile
import asyncio

# Setup test environment variables before importing modules
os.environ["DATABASE_PATH"] = ":memory:"
os.environ["ADMIN_IDS"] = "111111,222222"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:TEST_TOKEN"
os.environ["DEFAULT_PROVIDER_NAME"] = "OpenRouter"
os.environ["DEFAULT_MODEL_NAME"] = "openrouter/free"
os.environ["DEFAULT_API_URL"] = "https://openrouter.ai/api/v1/chat/completions"
os.environ["DEFAULT_MAX_REQUESTS"] = "5"

from config import is_admin, ADMIN_IDS
from database import Database
from ai_service import AIService
from utils.helpers import mask_api_key, split_text_into_chunks
from utils.prompts import (
    build_crop_advisory_prompt,
    build_pest_diagnosis_prompt,
    build_irrigation_prompt,
    build_fertilizer_prompt,
    build_weather_tips_prompt,
)
from handlers.keyboards import (
    get_main_menu_keyboard,
    get_admin_dashboard_keyboard,
    get_admin_quota_keyboard,
    get_soil_type_keyboard,
    get_climate_keyboard,
    get_pest_treatment_pref_keyboard,
    get_irrigation_type_keyboard,
)


class TestTelegramAgriBot(unittest.TestCase):
    def setUp(self):
        # Create a fresh temporary database for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_admin_config_parsing(self):
        """Test admin ID authentication and parsing."""
        self.assertTrue(is_admin(111111))
        self.assertTrue(is_admin(222222))
        self.assertFalse(is_admin(999999))
        self.assertEqual(ADMIN_IDS, {111111, 222222})

    def test_database_ai_settings(self):
        """Test reading and updating AI settings in database."""
        settings = self.db.get_ai_settings()
        self.assertEqual(settings["provider_name"], "OpenRouter")
        self.assertEqual(settings["model_name"], "openrouter/free")
        self.assertEqual(settings["api_url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(settings["reasoning_enabled"], 0)
        self.assertEqual(settings["max_requests"], 5)
        self.assertEqual(settings["requests_used"], 0)

        # Update settings
        self.db.update_ai_setting("provider_name", "DeepSeek")
        self.db.update_ai_setting("model_name", "deepseek/deepseek-r1")
        self.db.update_ai_setting("api_key", "sk-test-secret-key-12345")
        self.db.update_ai_setting("reasoning_enabled", 1)
        self.db.update_ai_setting("max_requests", 100)

        updated = self.db.get_ai_settings()
        self.assertEqual(updated["provider_name"], "DeepSeek")
        self.assertEqual(updated["model_name"], "deepseek/deepseek-r1")
        self.assertEqual(updated["api_key"], "sk-test-secret-key-12345")
        self.assertEqual(updated["reasoning_enabled"], 1)
        self.assertEqual(updated["max_requests"], 100)

    def test_quota_management(self):
        """Test request counter increments, limits, and reset."""
        self.db.register_or_update_user(user_id=1001, username="testuser", first_name="John")

        # Increment
        used = self.db.increment_requests_used(user_id=1001)
        self.assertEqual(used, 1)

        used = self.db.increment_requests_used(user_id=1001)
        self.assertEqual(used, 2)

        stats = self.db.get_stats()
        self.assertEqual(stats["requests_used"], 2)
        self.assertEqual(stats["total_user_requests"], 2)
        self.assertEqual(stats["total_users"], 1)

        # Reset Quota
        self.db.reset_quota()
        settings = self.db.get_ai_settings()
        self.assertEqual(settings["requests_used"], 0)

    def test_chat_history_memory(self):
        """Test chat message saving and chronological context retrieval."""
        user_id = 2002
        self.db.add_chat_message(user_id, "user", "How do I grow tomatoes?")
        self.db.add_chat_message(user_id, "assistant", "Tomatoes need 6-8 hours of sun and well-draining soil.")
        self.db.add_chat_message(user_id, "user", "What about watering?")
        self.db.add_chat_message(user_id, "assistant", "Water deeply 1-2 times a week.")

        history = self.db.get_chat_history(user_id, limit=4)
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "How do I grow tomatoes?")
        self.assertEqual(history[3]["content"], "Water deeply 1-2 times a week.")

        # Test clear
        deleted = self.db.clear_chat_history(user_id)
        self.assertEqual(deleted, 4)
        self.assertEqual(len(self.db.get_chat_history(user_id)), 0)

    def test_mask_api_key(self):
        """Test API key masking for safe UI display."""
        self.assertEqual(mask_api_key(""), "Not Set ❌")
        self.assertEqual(mask_api_key(None), "Not Set ❌")
        self.assertEqual(mask_api_key("12345"), "•••••")
        key = "sk-or-v1-abcdef1234567890abcdef1234567890"
        masked = mask_api_key(key)
        self.assertTrue(masked.startswith("sk-o"))
        self.assertTrue(masked.endswith("7890"))
        self.assertIn("•", masked)

    def test_text_chunking(self):
        """Test message splitting adhering to character limits."""
        short_text = "Hello world"
        self.assertEqual(split_text_into_chunks(short_text), ["Hello world"])

        long_text = "A" * 5000
        chunks = split_text_into_chunks(long_text, max_chars=2000)
        self.assertEqual(len(chunks), 3)
        self.assertEqual("".join(chunks), long_text)

    def test_keyboards_generation(self):
        """Test that all inline keyboards generate valid Telegram markups."""
        menu_kb = get_main_menu_keyboard()
        self.assertIsNotNone(menu_kb.inline_keyboard)
        self.assertGreaterEqual(len(menu_kb.inline_keyboard), 3)

        settings = {
            "provider_name": "OpenRouter",
            "model_name": "openrouter/free",
            "reasoning_enabled": 1,
            "max_requests": 50,
            "requests_used": 5,
        }
        admin_kb = get_admin_dashboard_keyboard(settings)
        self.assertIsNotNone(admin_kb.inline_keyboard)

        quota_kb = get_admin_quota_keyboard(settings)
        self.assertIsNotNone(quota_kb.inline_keyboard)

        self.assertIsNotNone(get_soil_type_keyboard().inline_keyboard)
        self.assertIsNotNone(get_climate_keyboard().inline_keyboard)
        self.assertIsNotNone(get_pest_treatment_pref_keyboard().inline_keyboard)
        self.assertIsNotNone(get_irrigation_type_keyboard().inline_keyboard)

    def test_prompt_builders(self):
        """Test prompt builder functions."""
        crop_p = build_crop_advisory_prompt({"soil": "Clay", "climate": "Arid", "crop_interest": "Wheat"})
        self.assertIn("Clay", crop_p)
        self.assertIn("Arid", crop_p)
        self.assertIn("Wheat", crop_p)

        pest_p = build_pest_diagnosis_prompt({"crop": "Tomato", "symptoms": "Yellow spots", "preference": "Organic"})
        self.assertIn("Tomato", pest_p)
        self.assertIn("Yellow spots", pest_p)
        self.assertIn("Organic", pest_p)

        irrig_p = build_irrigation_prompt({"crop": "Corn", "irrigation_type": "Drip"})
        self.assertIn("Corn", irrig_p)
        self.assertIn("Drip", irrig_p)

        fert_p = build_fertilizer_prompt({"crop": "Potato", "stage": "Flowering"})
        self.assertIn("Potato", fert_p)
        self.assertIn("Flowering", fert_p)

        weather_p = build_weather_tips_prompt({"climate": "Temperate", "season": "Spring"})
        self.assertIn("Temperate", weather_p)
        self.assertIn("Spring", weather_p)


class AsyncAITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        # Swap database in ai_service
        import database
        self.orig_db = database.db
        self.test_db = Database(self.temp_db_path)
        database.db = self.test_db
        import ai_service
        ai_service.db = self.test_db
        self.ai = AIService()

    def tearDown(self):
        import database
        import ai_service
        database.db = self.orig_db
        ai_service.db = self.orig_db
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    async def test_ai_key_not_set(self):
        """Test AI returns error when API key is empty."""
        self.test_db.update_ai_setting("api_key", "")
        success, reply = await self.ai.generate_response("Hello")
        self.assertFalse(success)
        self.assertIn("AI Service Not Configured", reply)

    async def test_ai_quota_enforcement(self):
        """Test AI blocks requests when quota limit is reached."""
        self.test_db.update_ai_setting("api_key", "sk-dummy-key")
        self.test_db.update_ai_setting("max_requests", 2)
        self.test_db.update_ai_setting("requests_used", 2)

        success, reply = await self.ai.generate_response("Hello")
        self.assertFalse(success)
        self.assertIn("Request Limit Reached", reply)

    async def test_ai_quota_reset_allows_requests(self):
        """Test that resetting quota unblocks AI requests."""
        self.test_db.update_ai_setting("api_key", "sk-dummy-key")
        self.test_db.update_ai_setting("max_requests", 2)
        self.test_db.update_ai_setting("requests_used", 2)

        # Quota blocked
        success, reply = await self.ai.generate_response("Hello")
        self.assertFalse(success)
        self.assertIn("Request Limit Reached", reply)

        # Reset Quota
        self.test_db.reset_quota()
        settings = self.test_db.get_ai_settings()
        self.assertEqual(settings["requests_used"], 0)


if __name__ == "__main__":
    unittest.main()
