"""
Inline and Reply Keyboards for TelegramAgriBot users and administrators.
"""

from typing import Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.helpers import mask_api_key


# =============================================================================
# User Keyboards
# =============================================================================

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Generate the primary agricultural services navigation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🌾 Crop & Soil Advisory", callback_data="wizard_crop"),
            InlineKeyboardButton("🐛 Pest & Disease Diagnosis", callback_data="wizard_pest"),
        ],
        [
            InlineKeyboardButton("💧 Irrigation & Water", callback_data="wizard_irrigation"),
            InlineKeyboardButton("🧪 Fertilizer & Nutrition", callback_data="wizard_fert"),
        ],
        [
            InlineKeyboardButton("🌦️ Seasonal & Weather Tips", callback_data="wizard_weather"),
            InlineKeyboardButton("💬 Ask AI Agronomist", callback_data="chat_mode"),
        ],
        [
            InlineKeyboardButton("🧹 Clear Chat History", callback_data="clear_history"),
            InlineKeyboardButton("ℹ️ Help & Guide", callback_data="user_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Single button to return to the main menu."""
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_soil_type_keyboard() -> InlineKeyboardMarkup:
    """Soil selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🌱 Loamy (Balanced)", callback_data="soil_loamy"),
            InlineKeyboardButton("🏖️ Sandy (Light/Fast)", callback_data="soil_sandy"),
        ],
        [
            InlineKeyboardButton("🧱 Clay (Heavy/Moist)", callback_data="soil_clay"),
            InlineKeyboardButton("🍂 Silty / Peaty (Rich)", callback_data="soil_silty"),
        ],
        [
            InlineKeyboardButton("❓ Not Sure / Other", callback_data="soil_other"),
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_climate_keyboard() -> InlineKeyboardMarkup:
    """Climate / Region keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("☀️ Arid & Semi-Arid", callback_data="clim_arid"),
            InlineKeyboardButton("🌊 Mediterranean", callback_data="clim_med"),
        ],
        [
            InlineKeyboardButton("🌴 Tropical / Subtropical", callback_data="clim_tropical"),
            InlineKeyboardButton("🌲 Temperate / Continental", callback_data="clim_temperate"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pest_treatment_pref_keyboard() -> InlineKeyboardMarkup:
    """Pest treatment preference selection."""
    keyboard = [
        [
            InlineKeyboardButton("🌿 100% Organic & Bio", callback_data="pestpref_organic"),
            InlineKeyboardButton("⚖️ Integrated IPM (Balanced)", callback_data="pestpref_ipm"),
        ],
        [
            InlineKeyboardButton("🧪 Fast-Acting Chemical", callback_data="pestpref_chemical"),
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_irrigation_type_keyboard() -> InlineKeyboardMarkup:
    """Irrigation method selection."""
    keyboard = [
        [
            InlineKeyboardButton("💧 Drip / Micro-irrigation", callback_data="irrig_drip"),
            InlineKeyboardButton("💦 Sprinkler / Pivot", callback_data="irrig_sprinkler"),
        ],
        [
            InlineKeyboardButton("🌊 Furrow / Flood", callback_data="irrig_flood"),
            InlineKeyboardButton("🌧️ Rainfed / Dryland", callback_data="irrig_rain"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# =============================================================================
# Admin Keyboards
# =============================================================================

def get_admin_dashboard_keyboard(settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """
    Construct the dynamic admin panel inline keyboard displaying current statuses.
    """
    provider = settings.get("provider_name", "OpenRouter")
    model = settings.get("model_name", "openrouter/free")
    reasoning_enabled = bool(settings.get("reasoning_enabled", 0))
    reasoning_label = "🟢 Enabled (ON)" if reasoning_enabled else "🔴 Disabled (OFF)"
    max_reqs = settings.get("max_requests", 50)
    used_reqs = settings.get("requests_used", 0)

    keyboard = [
        [
            InlineKeyboardButton(f"🏷️ Provider: {provider}", callback_data="admin_edit_provider"),
            InlineKeyboardButton(f"🤖 Model: {model}", callback_data="admin_edit_model"),
        ],
        [
            InlineKeyboardButton("🌐 Endpoint API URL", callback_data="admin_edit_url"),
            InlineKeyboardButton("🔑 Update API Key", callback_data="admin_edit_key"),
        ],
        [
            InlineKeyboardButton(
                f"🧠 Advanced Reasoning: {reasoning_label}",
                callback_data="admin_toggle_reasoning",
            ),
        ],
        [
            InlineKeyboardButton(
                f"📊 Quotas & Limits ({used_reqs}/{max_reqs})",
                callback_data="admin_quota_menu",
            ),
            InlineKeyboardButton("⚡ Test AI Connection", callback_data="admin_test_ai"),
        ],
        [
            InlineKeyboardButton("📈 System Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("❌ Exit Admin Panel", callback_data="admin_close"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_quota_keyboard(settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Quota and limit management keyboard."""
    max_reqs = settings.get("max_requests", 50)
    used_reqs = settings.get("requests_used", 0)
    remaining = max(0, max_reqs - used_reqs) if max_reqs > 0 else "Unlimited"

    keyboard = [
        [
            InlineKeyboardButton(f"✏️ Change Max Limit (Current: {max_reqs})", callback_data="admin_edit_max_requests"),
        ],
        [
            InlineKeyboardButton("🔄 Reset Quota Counter (Set Used to 0)", callback_data="admin_reset_quota"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Admin Dashboard", callback_data="admin_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel admin input state."""
    keyboard = [
        [InlineKeyboardButton("🔙 Cancel & Return to Admin Panel", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)
