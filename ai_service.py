"""
AI Service layer for TelegramAgriBot.
Communicates with OpenRouter, OpenAI, DeepSeek, and OpenAI-compatible Chat Completion APIs.
Supports dynamic endpoints, API keys, advanced reasoning payloads, and quota limits.
"""

import logging
import httpx
from typing import List, Dict, Tuple, Optional
from database import db
from utils.prompts import AGRONOMIST_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.timeout = httpx.Timeout(90.0, connect=15.0)

    async def generate_response(
        self,
        user_message: str,
        user_id: Optional[int] = None,
        system_prompt: Optional[str] = None,
        include_history: bool = True,
    ) -> Tuple[bool, str]:
        """
        Generate AI completion for a given user message.
        Returns:
            (success: bool, response_text: str)
        """
        settings = db.get_ai_settings()
        provider_name = settings.get("provider_name", "OpenRouter")
        model_name = settings.get("model_name", "openrouter/free")
        api_url = settings.get("api_url", "https://openrouter.ai/api/v1/chat/completions")
        api_key = settings.get("api_key", "").strip()
        reasoning_enabled = bool(settings.get("reasoning_enabled", 0))
        max_requests = settings.get("max_requests", 50)
        requests_used = settings.get("requests_used", 0)

        # 1. Check API Key
        if not api_key:
            return (
                False,
                "⚠️ *AI Service Not Configured*\n\n"
                "The bot administrator has not configured the API Key yet.\n"
                "If you are the administrator, please use `/admin` to set your API Key.",
            )

        # 2. Check Quota Limits (0 means unlimited)
        if max_requests > 0 and requests_used >= max_requests:
            return (
                False,
                f"🛑 *Request Limit Reached*\n\n"
                f"The bot has reached its configured limit of **{max_requests}** requests "
                f"(Used: **{requests_used}**).\n\n"
                f"Please contact the bot administrator to increase or reset the quota.",
            )

        # 3. Assemble Messages Payload
        messages: List[Dict[str, str]] = []
        messages.append({
            "role": "system",
            "content": system_prompt or AGRONOMIST_SYSTEM_PROMPT,
        })

        if include_history and user_id:
            past_messages = db.get_chat_history(user_id=user_id, limit=6)
            for msg in past_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        # 4. Construct Request Payload
        payload: Dict[str, any] = {
            "model": model_name,
            "messages": messages,
        }

        # Add Advanced Reasoning if enabled
        if reasoning_enabled:
            payload["reasoning"] = {"enabled": True}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TelegramAgriBot",
            "X-Title": "TelegramAgriBot",
        }

        # 5. Send HTTP Request
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(api_url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    return False, "❌ Received empty choices from AI provider."

                message_obj = choices[0].get("message", {})
                content = message_obj.get("content", "").strip()

                # Some reasoning models put content in reasoning or reasoning_content
                reasoning_text = message_obj.get("reasoning", "") or message_obj.get("reasoning_content", "")
                if not content and reasoning_text:
                    content = reasoning_text.strip()

                if not content:
                    return False, "❌ AI response contained no text content."

                # Increment quota counter
                new_count = db.increment_requests_used(user_id=user_id)
                logger.info(f"AI request successful for user {user_id}. Quota used: {new_count}/{max_requests}")

                # Save to user chat history
                if user_id:
                    db.add_chat_message(user_id, "user", user_message)
                    db.add_chat_message(user_id, "assistant", content)

                return True, content

            elif response.status_code == 401:
                return (
                    False,
                    "❌ *Authentication Error (401)*\n"
                    "Invalid API Key. Please verify the API Key in the `/admin` panel.",
                )
            elif response.status_code == 402:
                return (
                    False,
                    "❌ *Payment Required (402)*\n"
                    "Your AI provider account has insufficient credits or active limits.",
                )
            elif response.status_code == 429:
                return (
                    False,
                    "⏳ *Rate Limit Exceeded (429)*\n"
                    "The AI provider is currently rate-limiting requests. Please try again in a few moments.",
                )
            else:
                error_detail = response.text[:300]
                logger.error(f"AI API Error {response.status_code}: {error_detail}")
                return (
                    False,
                    f"❌ *AI Provider Error ({response.status_code})*\n"
                    f"```{error_detail}```",
                )

        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to AI provider {api_url}")
            return (
                False,
                "⏱️ *Request Timed Out*\n"
                "The AI model took too long to generate a response. Please try again.",
            )
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to {api_url}: {e}")
            return (
                False,
                f"🌐 *Network Connection Error*\n"
                f"Failed to connect to `{api_url}`. Details: {e}",
            )
        except Exception as e:
            logger.exception(f"Unexpected error in AI service: {e}")
            return False, f"⚠️ *Unexpected Error*: {str(e)}"

    async def test_connection(self) -> Tuple[bool, str]:
        """Test the current AI settings with a minimal ping query."""
        test_prompt = "Reply with 'OK' if you can read this."
        success, reply = await self.generate_response(
            user_message=test_prompt,
            user_id=None,
            system_prompt="You are a health check system. Reply with 'OK'.",
            include_history=False,
        )
        return success, reply


ai_service = AIService()
