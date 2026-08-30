"""
Helper utilities for TelegramAgriBot: Safe message delivery, text formatting, and masking.
"""

import logging
from typing import List, Optional
from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from config import is_admin

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LENGTH = 4000


def mask_api_key(key: Optional[str]) -> str:
    """Return a masked representation of an API key for safe UI display."""
    if not key:
        return "Not Set ❌"
    clean_key = key.strip()
    if len(clean_key) <= 8:
        return "•" * len(clean_key)
    # Show first 4 characters and last 4 characters, mask the middle
    prefix = clean_key[:4]
    suffix = clean_key[-4:]
    masked_middle = "•" * min(len(clean_key) - 8, 24)
    return f"{prefix}{masked_middle}{suffix}"


def split_text_into_chunks(text: str, max_chars: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> List[str]:
    """Split long text into readable chunks adhering to Telegram character limits."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current_chunk = []
    current_length = 0

    lines = text.split("\n")
    for line in lines:
        if current_length + len(line) + 1 > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            # If a single line is extraordinarily long, split by characters
            if len(line) > max_chars:
                for i in range(0, len(line), max_chars):
                    chunks.append(line[i : i + max_chars])
                continue

        current_chunk.append(line)
        current_length += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


async def safe_send_message(
    update: Update,
    text: str,
    reply_markup=None,
    parse_mode: str = ParseMode.MARKDOWN,
) -> Optional[Message]:
    """
    Safely send a message using markdown with fallback to plain text on formatting errors.
    Automatically splits long responses into chunks.
    """
    target = update.effective_message
    if not target or not target.chat:
        return None

    chunks = split_text_into_chunks(text)
    last_sent_message = None

    for idx, chunk in enumerate(chunks):
        # Only attach reply_markup to the final chunk
        markup = reply_markup if idx == len(chunks) - 1 else None

        try:
            last_sent_message = await target.reply_text(
                text=chunk,
                reply_markup=markup,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
        except BadRequest as e:
            logger.warning(f"Telegram formatting failed with {parse_mode} ({e}). Falling back to plain text.")
            # Fallback to plain text without parse_mode
            last_sent_message = await target.reply_text(
                text=chunk,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Error delivering message: {e}")
            try:
                last_sent_message = await target.reply_text(
                    text=chunk,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
            except Exception as inner_e:
                logger.error(f"Fatal error delivering plain text: {inner_e}")

    return last_sent_message
