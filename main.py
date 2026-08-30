"""
TelegramAgriBot - Main Application Entrypoint.
A modern, asynchronous AI-powered Agricultural Consultant for Telegram.
"""

import sys
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS
from database import db
from handlers.admin_handlers import (
    admin_command,
    admin_conv_handler,
    admin_callback_handler,
)
from handlers.user_handlers import (
    start_command,
    help_command,
    menu_command,
    clear_command,
    user_callback_handler,
    handle_user_text_chat,
    crop_wizard_handler,
    pest_wizard_handler,
    irrigation_wizard_handler,
    fert_wizard_handler,
    weather_wizard_handler,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AgriBot")


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected errors caused by Updates."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)


def main():
    """Initialize and run TelegramAgriBot."""
    # Check Token
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith(":-"):
        logger.error(
            "TELEGRAM_BOT_TOKEN is missing or empty! "
            "Please create a .env file based on .env.example and set your bot token from @BotFather."
        )
        sys.exit(1)

    logger.info("Initializing TelegramAgriBot...")
    logger.info(f"Configured Admins: {list(ADMIN_IDS) if ADMIN_IDS else 'None specified'}")

    # Build Application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register Error Handler
    app.add_error_handler(global_error_handler)

    # 1. Admin Handlers (Conversation handler first for state precedence)
    app.add_handler(admin_conv_handler)
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))

    # 2. Agricultural Wizard Handlers (Conversation handlers)
    app.add_handler(crop_wizard_handler)
    app.add_handler(pest_wizard_handler)
    app.add_handler(irrigation_wizard_handler)
    app.add_handler(fert_wizard_handler)
    app.add_handler(weather_wizard_handler)

    # 3. User Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("clear", clear_command))

    # 4. User Navigation Callbacks
    app.add_handler(
        CallbackQueryHandler(
            user_callback_handler,
            pattern="^(main_menu|clear_history|user_help|chat_mode)$",
        )
    )

    # 5. Free-form AI Chat Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text_chat))

    # Start Polling
    logger.info("🌿 AgriBot is up and running! Polling for updates...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
