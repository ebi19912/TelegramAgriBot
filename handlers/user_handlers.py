"""
User interaction handlers and guided agronomy wizards for TelegramAgriBot.
All user-facing messages, buttons, and prompts are in English.
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
from database import db
from ai_service import ai_service
from utils.helpers import safe_send_message
from utils.prompts import (
    build_crop_advisory_prompt,
    build_pest_diagnosis_prompt,
    build_irrigation_prompt,
    build_fertilizer_prompt,
    build_weather_tips_prompt,
)
from handlers.keyboards import (
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_soil_type_keyboard,
    get_climate_keyboard,
    get_pest_treatment_pref_keyboard,
    get_irrigation_type_keyboard,
)

logger = logging.getLogger(__name__)

# Wizard States
(
    CROP_SOIL,
    CROP_CLIMATE,
    CROP_TARGET,
    PEST_SYMPTOMS,
    PEST_PREF,
    IRRIG_SYSTEM,
    IRRIG_DETAILS,
    FERT_DETAILS,
    WEATHER_CLIMATE,
) = range(200, 209)


# =============================================================================
# Basic Commands (/start, /menu, /help, /clear)
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command. Registers user and presents main menu."""
    user = update.effective_user
    if user:
        db.register_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

    welcome_text = (
        f"🌿 *Welcome to AgriBot, {user.first_name if user else 'Friend'}!* 🚜\n\n"
        "I am your specialized **AI Agronomist & Agricultural Consultant**.\n"
        "I can help you with:\n"
        "• 🌾 *Crop & Soil Advisory*: Variety selection and soil prep.\n"
        "• 🐛 *Pest & Disease Diagnosis*: Symptoms, organic & chemical remedies.\n"
        "• 💧 *Irrigation Management*: Water schedules and conservation.\n"
        "• 🧪 *Fertilizer & Nutrition*: NPK ratios, deficiencies & composting.\n"
        "• 🌦️ *Seasonal Tips*: Weather mitigation and best practices.\n\n"
        "👇 *Choose a service below, or simply type any agricultural question directly!*"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📖 *AgriBot Help & User Guide*\n\n"
        "*Available Commands:*\n"
        "• `/start` — Start bot and display main services menu\n"
        "• `/menu` — Open the services menu\n"
        "• `/clear` — Clear your conversation memory/history\n"
        "• `/help` — Display this guide\n\n"
        "*💡 Pro Tips for Best Answers:*\n"
        "1. Mention your **crop type** and **growth stage** (e.g., flowering tomato).\n"
        "2. Describe **soil texture** and **watering frequency** when asking about plant health.\n"
        "3. Describe **symptoms precisely** (e.g., yellow spots on lower leaves, powdery coating).\n"
        "4. You can ask follow-up questions naturally in the chat!"
    )
    await safe_send_message(update, help_text, reply_markup=get_back_to_menu_keyboard())


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command."""
    await update.message.reply_text(
        "🌾 *AgriBot Main Services Menu*\nSelect an option below:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command to reset user conversation context."""
    user = update.effective_user
    if user:
        count = db.clear_chat_history(user.id)
        await update.message.reply_text(
            f"🧹 *Chat memory cleared successfully!* ({count} messages reset)\n"
            "You can start a fresh conversation now.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


# =============================================================================
# Callback Navigation Handler
# =============================================================================

async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle standard user menu callback clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🌾 *AgriBot Main Services Menu*\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "clear_history":
        user = update.effective_user
        if user:
            db.clear_chat_history(user.id)
        await query.edit_message_text(
            "🧹 *Conversation memory cleared!* You are starting with a clean slate.\n\n"
            "What would you like to ask today?",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "user_help":
        help_text = (
            "📖 *AgriBot Help & User Guide*\n\n"
            "*Available Commands:*\n"
            "• `/start` — Start bot and display main services menu\n"
            "• `/menu` — Open the services menu\n"
            "• `/clear` — Clear your conversation memory/history\n"
            "• `/help` — Display this guide\n\n"
            "*💡 Pro Tips for Best Answers:*\n"
            "1. Mention your **crop type** and **growth stage** (e.g., flowering tomato).\n"
            "2. Describe **soil texture** and **watering frequency** when asking about plant health.\n"
            "3. Describe **symptoms precisely** (e.g., yellow spots on lower leaves, powdery coating).\n"
            "4. You can ask follow-up questions naturally in the chat!"
        )
        await query.edit_message_text(
            help_text,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "chat_mode":
        await query.edit_message_text(
            "💬 *Direct AI Agronomist Chat Active*\n\n"
            "Type any question about farming, plant diseases, fertilizers, or gardening below and send it!",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


# =============================================================================
# Crop Advisory Wizard Flow
# =============================================================================

async def start_crop_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start Crop & Soil Advisory Wizard."""
    query = update.callback_query
    await query.answer()
    context.user_data["crop_wizard"] = {}

    await query.edit_message_text(
        "🌾 *Crop & Soil Advisory Wizard — Step 1/3*\n\n"
        "Please select your farm or garden's primary **Soil Type**:",
        reply_markup=get_soil_type_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return CROP_SOIL


async def handle_crop_soil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save soil type and ask for climate."""
    query = update.callback_query
    await query.answer()
    data = query.data

    soil_map = {
        "soil_loamy": "Loamy Soil (Fertile & Well-draining)",
        "soil_sandy": "Sandy Soil (Light & Fast-draining)",
        "soil_clay": "Clay Soil (Heavy & High Moisture)",
        "soil_silty": "Silty / Peaty Soil (Organic Rich)",
        "soil_other": "Mixed / Other Soil",
    }
    context.user_data["crop_wizard"]["soil"] = soil_map.get(data, "Standard Agricultural Soil")

    await query.edit_message_text(
        "🌾 *Crop & Soil Advisory Wizard — Step 2/3*\n\n"
        f"Selected Soil: *{context.user_data['crop_wizard']['soil']}*\n\n"
        "Now, select your **Regional Climate**:",
        reply_markup=get_climate_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return CROP_CLIMATE


async def handle_crop_climate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save climate and ask for target crop."""
    query = update.callback_query
    await query.answer()
    data = query.data

    climate_map = {
        "clim_arid": "Arid / Semi-Arid (Hot & Dry)",
        "clim_med": "Mediterranean (Mild Winters, Dry Summers)",
        "clim_tropical": "Tropical / Subtropical (Warm & Humid)",
        "clim_temperate": "Temperate / Continental (Moderate 4 seasons)",
    }
    context.user_data["crop_wizard"]["climate"] = climate_map.get(data, "Temperate Climate")

    await query.edit_message_text(
        "🌾 *Crop & Soil Advisory Wizard — Step 3/3*\n\n"
        f"• Soil: *{context.user_data['crop_wizard']['soil']}*\n"
        f"• Climate: *{context.user_data['crop_wizard']['climate']}*\n\n"
        "✍️ *Please type your target crop or question:*\n"
        "_(e.g., 'Wheat and Barley', 'Greenhouse Tomatoes', 'Recommend best profitable crops')_",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return CROP_TARGET


async def handle_crop_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process crop target and query AI."""
    user = update.effective_user
    user_text = update.message.text.strip()
    wizard_data = context.user_data.get("crop_wizard", {})
    wizard_data["crop_interest"] = user_text
    wizard_data["season"] = "Current upcoming planting season"
    wizard_data["farm_size"] = "Field/Garden scale"

    prompt = build_crop_advisory_prompt(wizard_data)

    await update.message.reply_chat_action(ChatAction.TYPING)
    status_msg = await update.message.reply_text("🌾 *Analyzing soil and crop compatibility with AI...*")

    success, reply = await ai_service.generate_response(
        user_message=prompt,
        user_id=user.id if user else None,
        include_history=False,
    )

    try:
        await status_msg.delete()
    except Exception:
        pass

    await safe_send_message(update, reply, reply_markup=get_back_to_menu_keyboard())
    context.user_data.pop("crop_wizard", None)
    return ConversationHandler.END


# =============================================================================
# Pest & Disease Diagnosis Wizard Flow
# =============================================================================

async def start_pest_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start Pest Diagnosis Wizard."""
    query = update.callback_query
    await query.answer()
    context.user_data["pest_wizard"] = {}

    await query.edit_message_text(
        "🐛 *Pest & Disease Diagnosis Wizard — Step 1/2*\n\n"
        "Please describe the problem you are seeing on your crop:\n"
        "• *Crop name* (e.g. Potato, Apple, Cucumber)\n"
        "• *Symptoms* (e.g. Yellow leaves, powdery white mildew, curling, holes, root rot)\n"
        "• *Any visible insects* (e.g. aphids, caterpillars, mites)\n\n"
        "✍️ *Type your description below:*",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return PEST_SYMPTOMS


async def handle_pest_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save symptoms and ask for treatment preference."""
    text = update.message.text.strip()
    context.user_data["pest_wizard"]["description"] = text
    context.user_data["pest_wizard"]["symptoms"] = text
    context.user_data["pest_wizard"]["crop"] = "Described crop"

    await update.message.reply_text(
        "🐛 *Pest & Disease Diagnosis Wizard — Step 2/2*\n\n"
        "Select your preferred treatment approach:",
        reply_markup=get_pest_treatment_pref_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return PEST_PREF


async def handle_pest_pref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate pest diagnosis response with AI."""
    query = update.callback_query
    await query.answer()
    data = query.data

    pref_map = {
        "pestpref_organic": "100% Organic & Biological Control",
        "pestpref_ipm": "Integrated Pest Management (IPM - Bio + Targeted Chemical)",
        "pestpref_chemical": "Fast-acting Conventional Agrochemicals",
    }
    context.user_data["pest_wizard"]["preference"] = pref_map.get(data, "Integrated Pest Management")

    wizard_data = context.user_data.get("pest_wizard", {})
    prompt = build_pest_diagnosis_prompt(wizard_data)

    user = update.effective_user
    await query.edit_message_text("🔍 *Diagnosing symptoms and generating treatment solutions with AI...*")

    success, reply = await ai_service.generate_response(
        user_message=prompt,
        user_id=user.id if user else None,
        include_history=False,
    )

    await safe_send_message(update, reply, reply_markup=get_back_to_menu_keyboard())
    context.user_data.pop("pest_wizard", None)
    return ConversationHandler.END


# =============================================================================
# Irrigation & Water Wizard Flow
# =============================================================================

async def start_irrigation_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start Irrigation Wizard."""
    query = update.callback_query
    await query.answer()
    context.user_data["irrig_wizard"] = {}

    await query.edit_message_text(
        "💧 *Irrigation & Water Management Wizard — Step 1/2*\n\n"
        "Select your **Irrigation System / Method**:",
        reply_markup=get_irrigation_type_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return IRRIG_SYSTEM


async def handle_irrig_system(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save irrigation system and ask for details."""
    query = update.callback_query
    await query.answer()
    data = query.data

    irrig_map = {
        "irrig_drip": "Drip / Micro-irrigation",
        "irrig_sprinkler": "Sprinkler / Center Pivot",
        "irrig_flood": "Furrow / Basin / Flood",
        "irrig_rain": "Rainfed / Dryland Farming",
    }
    context.user_data["irrig_wizard"]["irrigation_type"] = irrig_map.get(data, "Drip Irrigation")

    await query.edit_message_text(
        "💧 *Irrigation & Water Management Wizard — Step 2/2*\n\n"
        f"System: *{context.user_data['irrig_wizard']['irrigation_type']}*\n\n"
        "✍️ *Please enter your Crop and any specific conditions:*\n"
        "_(e.g., 'Almond orchard in sandy soil, summer watering schedule', or 'Corn flowering stage')_",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return IRRIG_DETAILS


async def handle_irrig_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process irrigation details and query AI."""
    user = update.effective_user
    user_text = update.message.text.strip()
    wizard_data = context.user_data.get("irrig_wizard", {})
    wizard_data["crop"] = user_text
    wizard_data["issue"] = user_text
    wizard_data["soil_type"] = "Loamy to Sandy"
    wizard_data["climate"] = "Temperate / Seasonal"

    prompt = build_irrigation_prompt(wizard_data)

    await update.message.reply_chat_action(ChatAction.TYPING)
    status_msg = await update.message.reply_text("💧 *Calculating optimal watering plan with AI...*")

    success, reply = await ai_service.generate_response(
        user_message=prompt,
        user_id=user.id if user else None,
        include_history=False,
    )

    try:
        await status_msg.delete()
    except Exception:
        pass

    await safe_send_message(update, reply, reply_markup=get_back_to_menu_keyboard())
    context.user_data.pop("irrig_wizard", None)
    return ConversationHandler.END


# =============================================================================
# Fertilizer & Nutrition Wizard Flow
# =============================================================================

async def start_fert_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start Fertilizer Wizard."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🧪 *Fertilizer & Soil Nutrition Calculator*\n\n"
        "✍️ *Please enter your Crop and details:*\n"
        "• Crop name & stage (e.g., Tomato early fruiting, Wheat tillering)\n"
        "• Any visible deficiencies (e.g., yellowing older leaves, purple stems)\n"
        "• Preferred fertilizer type (Organic, NPK synthetic, Fertigation)\n\n"
        "Type your message below:",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return FERT_DETAILS


async def handle_fert_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate fertilizer advice from AI."""
    user = update.effective_user
    user_text = update.message.text.strip()

    prompt = build_fertilizer_prompt({
        "crop": user_text,
        "stage": "Active growth stage",
        "symptoms": user_text,
        "fertilizer_pref": "Balanced NPK + Organic amendments",
    })

    await update.message.reply_chat_action(ChatAction.TYPING)
    status_msg = await update.message.reply_text("🧪 *Formulating nutrient schedule with AI...*")

    success, reply = await ai_service.generate_response(
        user_message=prompt,
        user_id=user.id if user else None,
        include_history=False,
    )

    try:
        await status_msg.delete()
    except Exception:
        pass

    await safe_send_message(update, reply, reply_markup=get_back_to_menu_keyboard())
    return ConversationHandler.END


# =============================================================================
# Seasonal & Weather Tips Wizard Flow
# =============================================================================

async def start_weather_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start Seasonal & Weather Tips Wizard."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🌦️ *Seasonal Farming & Weather Guidance*\n\n"
        "Select your climate zone to receive seasonal protective tips and checklists:",
        reply_markup=get_climate_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return WEATHER_CLIMATE


async def handle_weather_climate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate seasonal tips."""
    query = update.callback_query
    await query.answer()
    data = query.data

    climate_map = {
        "clim_arid": "Arid / Desert Climate",
        "clim_med": "Mediterranean Climate",
        "clim_tropical": "Tropical Climate",
        "clim_temperate": "Temperate 4-Season Climate",
    }
    climate = climate_map.get(data, "Temperate Climate")

    prompt = build_weather_tips_prompt({
        "climate": climate,
        "season": "Upcoming seasonal shift",
        "crops": "Vegetables, Cereals, and Fruit trees",
        "event": "Seasonal protection and preparation",
    })

    user = update.effective_user
    await query.edit_message_text("🌦️ *Generating seasonal farming guide with AI...*")

    success, reply = await ai_service.generate_response(
        user_message=prompt,
        user_id=user.id if user else None,
        include_history=False,
    )

    await safe_send_message(update, reply, reply_markup=get_back_to_menu_keyboard())
    return ConversationHandler.END


async def cancel_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any active wizard and return to main menu."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🌾 *AgriBot Main Services Menu*\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "🌾 *AgriBot Main Services Menu*\nSelect an option below:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    return ConversationHandler.END


# =============================================================================
# Free-form Text Message Handler (Direct AI Chat)
# =============================================================================

async def handle_user_text_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle general text messages sent by user (outside of wizards).
    Maintains conversational memory context.
    """
    user = update.effective_user
    user_message = update.message.text.strip()

    if not user_message:
        return

    if user:
        db.register_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

    # Show typing indicator
    await update.message.reply_chat_action(ChatAction.TYPING)

    # Generate response
    success, reply = await ai_service.generate_response(
        user_message=user_message,
        user_id=user.id if user else None,
        include_history=True,
    )

    await safe_send_message(update, reply, reply_markup=get_back_to_menu_keyboard())


# =============================================================================
# Conversation Handlers Registration
# =============================================================================

crop_wizard_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_crop_wizard, pattern="^wizard_crop$")],
    states={
        CROP_SOIL: [CallbackQueryHandler(handle_crop_soil, pattern="^soil_")],
        CROP_CLIMATE: [CallbackQueryHandler(handle_crop_climate, pattern="^clim_")],
        CROP_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_crop_target)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_wizard, pattern="^main_menu$"),
        CommandHandler("cancel", cancel_wizard),
    ],
)

pest_wizard_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_pest_wizard, pattern="^wizard_pest$")],
    states={
        PEST_SYMPTOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pest_symptoms)],
        PEST_PREF: [CallbackQueryHandler(handle_pest_pref, pattern="^pestpref_")],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_wizard, pattern="^main_menu$"),
        CommandHandler("cancel", cancel_wizard),
    ],
)

irrigation_wizard_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_irrigation_wizard, pattern="^wizard_irrigation$")],
    states={
        IRRIG_SYSTEM: [CallbackQueryHandler(handle_irrig_system, pattern="^irrig_")],
        IRRIG_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_irrig_details)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_wizard, pattern="^main_menu$"),
        CommandHandler("cancel", cancel_wizard),
    ],
)

fert_wizard_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_fert_wizard, pattern="^wizard_fert$")],
    states={
        FERT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fert_details)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_wizard, pattern="^main_menu$"),
        CommandHandler("cancel", cancel_wizard),
    ],
)

weather_wizard_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_weather_wizard, pattern="^wizard_weather$")],
    states={
        WEATHER_CLIMATE: [CallbackQueryHandler(handle_weather_climate, pattern="^clim_")],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_wizard, pattern="^main_menu$"),
        CommandHandler("cancel", cancel_wizard),
    ],
)
