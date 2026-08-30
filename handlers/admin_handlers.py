"""
Admin panel handlers for TelegramAgriBot.
Allows administrators to manage AI providers, models, endpoint URLs, API keys,
reasoning parameters, and request quotas directly via Telegram.
"""

import logging
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from config import is_admin
from database import db
from ai_service import ai_service
from utils.helpers import mask_api_key, safe_send_message
from handlers.keyboards import (
    get_admin_dashboard_keyboard,
    get_admin_quota_keyboard,
    get_admin_cancel_keyboard,
)

logger = logging.getLogger(__name__)

# Conversation States for Admin edits
(
    WAITING_PROVIDER,
    WAITING_MODEL,
    WAITING_URL,
    WAITING_KEY,
    WAITING_MAX_REQUESTS,
) = range(100, 105)


def _format_admin_dashboard_text(settings: dict) -> str:
    """Format the main administration dashboard text."""
    provider = settings.get("provider_name", "OpenRouter")
    model = settings.get("model_name", "openrouter/free")
    api_url = settings.get("api_url", "https://openrouter.ai/api/v1/chat/completions")
    api_key = settings.get("api_key", "")
    reasoning = "🟢 Enabled" if settings.get("reasoning_enabled", 0) else "🔴 Disabled"
    max_reqs = settings.get("max_requests", 50)
    used_reqs = settings.get("requests_used", 0)
    remaining = max(0, max_reqs - used_reqs) if max_reqs > 0 else "Unlimited"

    return (
        "⚙️ *AgriBot Administration & AI Config*\n\n"
        f"🏷️ *Provider Name*: `{provider}`\n"
        f"🤖 *Model Name*: `{model}`\n"
        f"🌐 *API URL*: `{api_url}`\n"
        f"🔑 *API Key*: `{mask_api_key(api_key)}`\n\n"
        f"🧠 *Enable Advanced Reasoning*: {reasoning}\n"
        "   _Sends `{'reasoning': {'enabled': true}}` in payload (DeepSeek/OpenRouter)_\n\n"
        "📊 *Quotas & Limits*:\n"
        f"   • *Max Requests*: `{max_reqs}`\n"
        f"   • *Used*: `{used_reqs}`\n"
        f"   • *Remaining*: `{remaining}`\n\n"
        "👇 _Select an option below to update settings:_"
    )


# =============================================================================
# Command Handler: /admin
# =============================================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command to launch administration panel."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text(
            "⛔ *Access Denied*\n\nYou are not authorized to view the admin panel.\n"
            "If you are the server administrator, add your Telegram ID to `ADMIN_IDS` in `.env`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    settings = db.get_ai_settings()
    text = _format_admin_dashboard_text(settings)
    keyboard = get_admin_dashboard_keyboard(settings)

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# =============================================================================
# Callback Handlers: Navigation and Toggles
# =============================================================================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin inline keyboard button clicks."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not user or not is_admin(user.id):
        await query.edit_message_text("⛔ Unauthorized access.")
        return

    data = query.data

    if data == "admin_main":
        settings = db.get_ai_settings()
        text = _format_admin_dashboard_text(settings)
        keyboard = get_admin_dashboard_keyboard(settings)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_toggle_reasoning":
        settings = db.get_ai_settings()
        current = bool(settings.get("reasoning_enabled", 0))
        new_val = 0 if current else 1
        db.update_ai_setting("reasoning_enabled", new_val)

        # Refresh dashboard
        updated_settings = db.get_ai_settings()
        text = _format_admin_dashboard_text(updated_settings)
        keyboard = get_admin_dashboard_keyboard(updated_settings)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_quota_menu":
        settings = db.get_ai_settings()
        max_reqs = settings.get("max_requests", 50)
        used_reqs = settings.get("requests_used", 0)
        remaining = max(0, max_reqs - used_reqs) if max_reqs > 0 else "Unlimited"

        text = (
            "📊 *Quotas & Limits Management*\n\n"
            "Set maximum request limits to prevent unexpected API costs.\n\n"
            f"• *Chatbot Max Requests*: `{max_reqs}`\n"
            f"• *Used*: `{used_reqs}`\n"
            f"• *Remaining*: `{remaining}`\n"
        )
        keyboard = get_admin_quota_keyboard(settings)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_reset_quota":
        db.reset_quota()
        settings = db.get_ai_settings()
        text = (
            "✅ *Quota Counter Reset Successfully!*\n\n"
            f"• *Used Requests*: `0`\n"
            f"• *Max Limit*: `{settings.get('max_requests', 50)}`"
        )
        keyboard = get_admin_quota_keyboard(settings)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_test_ai":
        await query.edit_message_text(
            "⏳ *Testing AI Connection...*\nSending test payload to configured endpoint...",
            parse_mode=ParseMode.MARKDOWN,
        )
        success, result = await ai_service.test_connection()
        settings = db.get_ai_settings()

        if success:
            status_text = (
                "✅ *AI Connection Test Succeeded!*\n\n"
                f"🤖 *Response*: `{result}`\n\n"
                f"Endpoint: `{settings.get('api_url')}`\n"
                f"Model: `{settings.get('model_name')}`"
            )
        else:
            status_text = (
                "❌ *AI Connection Test Failed*\n\n"
                f"Error Details:\n{result}\n\n"
                "Please verify your API Key, URL, or model name."
            )

        keyboard = get_admin_dashboard_keyboard(settings)
        await query.message.reply_text(status_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_stats":
        stats = db.get_stats()
        text = (
            "📈 *AgriBot System Statistics*\n\n"
            f"👥 *Total Registered Users*: `{stats['total_users']}`\n"
            f"💬 *Total User Inquiries*: `{stats['total_user_requests']}`\n"
            f"📊 *Global AI Quota Used*: `{stats['requests_used']} / {stats['max_requests']}`\n"
            f"🤖 *Active Model*: `{stats['model_name']}` ({stats['provider_name']})\n"
            f"🧠 *Reasoning Mode*: `{'Enabled' if stats['reasoning_enabled'] else 'Disabled'}`"
        )
        keyboard = get_admin_dashboard_keyboard(db.get_ai_settings())
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_close":
        await query.edit_message_text("🔒 Admin panel closed. Use `/admin` to reopen anytime.")


# =============================================================================
# State Handlers for Editing AI Parameters
# =============================================================================

async def prompt_edit_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin for new provider name."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏷️ *Edit AI Provider Name*\n\n"
        "Enter the name of your AI provider (e.g. `OpenRouter`, `OpenAI`, `DeepSeek`, `Custom`):",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_PROVIDER


async def save_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save new provider name."""
    new_provider = update.message.text.strip()
    db.update_ai_setting("provider_name", new_provider)
    settings = db.get_ai_settings()

    await update.message.reply_text(
        f"✅ Provider updated to: *{new_provider}*\n\n" + _format_admin_dashboard_text(settings),
        reply_markup=get_admin_dashboard_keyboard(settings),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def prompt_edit_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin for new model name."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🤖 *Edit AI Model Name*\n\n"
        "Enter the model identifier, for example:\n"
        "• `openrouter/free`\n"
        "• `deepseek/deepseek-r1`\n"
        "• `openai/gpt-4o-mini`\n"
        "• `anthropic/claude-3.5-sonnet`\n"
        "• `google/gemini-2.5-flash`",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_MODEL


async def save_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save new model identifier."""
    new_model = update.message.text.strip()
    db.update_ai_setting("model_name", new_model)
    settings = db.get_ai_settings()

    await update.message.reply_text(
        f"✅ Model updated to: `{new_model}`\n\n" + _format_admin_dashboard_text(settings),
        reply_markup=get_admin_dashboard_keyboard(settings),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def prompt_edit_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin for API endpoint URL."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌐 *Edit API Endpoint URL*\n\n"
        "Enter the full Chat Completions endpoint URL, for example:\n"
        "• `https://openrouter.ai/api/v1/chat/completions`\n"
        "• `https://api.openai.com/v1/chat/completions`\n"
        "• `https://api.deepseek.com/chat/completions`",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_URL


async def save_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save new API endpoint URL."""
    new_url = update.message.text.strip()
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        await update.message.reply_text(
            "⚠️ Invalid URL format. Please start with `http://` or `https://`:",
            reply_markup=get_admin_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_URL

    db.update_ai_setting("api_url", new_url)
    settings = db.get_ai_settings()

    await update.message.reply_text(
        f"✅ API URL updated to:\n`{new_url}`\n\n" + _format_admin_dashboard_text(settings),
        reply_markup=get_admin_dashboard_keyboard(settings),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def prompt_edit_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin for new API key."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 *Update AI API Key (Bearer Token)*\n\n"
        "Please send your API key (e.g. `sk-or-v1-...`).\n\n"
        "🔒 _Your key is stored securely in the database and masked in the UI._",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_KEY


async def save_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save new API key."""
    new_key = update.message.text.strip()
    db.update_ai_setting("api_key", new_key)
    settings = db.get_ai_settings()

    # Delete message containing sensitive API key from chat if possible
    try:
        await update.message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message(
        f"✅ API Key updated securely (`{mask_api_key(new_key)}`)!\n\n"
        + _format_admin_dashboard_text(settings),
        reply_markup=get_admin_dashboard_keyboard(settings),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def prompt_edit_max_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin for new maximum request limit."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 *Set Maximum Request Limit*\n\n"
        "Enter the maximum number of AI requests allowed (e.g., `50`, `100`, `500`).\n"
        "💡 _Enter `0` for unlimited requests._",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_MAX_REQUESTS


async def save_max_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save new maximum request limit."""
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "⚠️ Please enter a valid non-negative integer (e.g. 50 or 0 for unlimited):",
            reply_markup=get_admin_cancel_keyboard(),
        )
        return WAITING_MAX_REQUESTS

    new_limit = int(text)
    db.update_ai_setting("max_requests", new_limit)
    settings = db.get_ai_settings()

    await update.message.reply_text(
        f"✅ Chatbot Max Requests set to: *{new_limit}*\n\n"
        + _format_admin_dashboard_text(settings),
        reply_markup=get_admin_dashboard_keyboard(settings),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


async def cancel_admin_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any ongoing admin edit operation."""
    query = update.callback_query
    if query:
        await query.answer()
        settings = db.get_ai_settings()
        await query.edit_message_text(
            _format_admin_dashboard_text(settings),
            reply_markup=get_admin_dashboard_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        settings = db.get_ai_settings()
        await update.message.reply_text(
            _format_admin_dashboard_text(settings),
            reply_markup=get_admin_dashboard_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )
    return ConversationHandler.END


# Conversation handler for Admin configuration
admin_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(prompt_edit_provider, pattern="^admin_edit_provider$"),
        CallbackQueryHandler(prompt_edit_model, pattern="^admin_edit_model$"),
        CallbackQueryHandler(prompt_edit_url, pattern="^admin_edit_url$"),
        CallbackQueryHandler(prompt_edit_key, pattern="^admin_edit_key$"),
        CallbackQueryHandler(prompt_edit_max_requests, pattern="^admin_edit_max_requests$"),
    ],
    states={
        WAITING_PROVIDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_provider)],
        WAITING_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_model)],
        WAITING_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_url)],
        WAITING_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_key)],
        WAITING_MAX_REQUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_max_requests)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_admin_conversation, pattern="^admin_main$"),
        CommandHandler("cancel", cancel_admin_conversation),
    ],
)
