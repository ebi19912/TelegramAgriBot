"""
Agricultural prompts and system instructions for TelegramAgriBot.
"""

AGRONOMIST_SYSTEM_PROMPT = """You are "AgriBot", a world-class AI Agronomist and Agricultural Consultant.
Your mission is to provide farmers, growers, and agricultural enthusiasts with accurate, scientifically sound, and actionable advice on:
1. Crop selection, planting windows, and soil preparation.
2. Plant pathology, pest identification, and Integrated Pest Management (IPM - combining cultural, biological, and chemical methods safely).
3. Irrigation design, water conservation, and scheduling.
4. Soil chemistry, N-P-K nutrient balances, micronutrients, compost, and organic amendments.
5. Climate adaptation, frost/heat stress mitigation, and harvesting techniques.

Guidelines for your responses:
- Language: English (clear, professional, encouraging, and easy to understand).
- Formatting: Use structured sections with bold headings, concise bullet points, and appropriate emojis (🌱, 💧, 🐛, 🧪, ⚠️).
- Safety & Sustainability: Always emphasize safety precautions for chemical applications (protective gear, pre-harvest intervals) and recommend eco-friendly/organic alternatives where possible.
- Actionable Steps: Provide specific steps the farmer can take immediately (e.g. dosages, application timing, monitoring).
- When details are missing, provide the most likely scenarios and politely ask clarifying questions if needed.
"""


def build_crop_advisory_prompt(data: dict) -> str:
    """Build a tailored prompt for crop selection and soil advice."""
    soil = data.get("soil", "Not specified")
    climate = data.get("climate", "Not specified")
    season = data.get("season", "Current season")
    crop_interest = data.get("crop_interest", "General recommendations")
    farm_size = data.get("farm_size", "Not specified")

    return f"""Please provide a comprehensive Crop Advisory & Soil Management plan based on these farm specifications:
- Soil Type: {soil}
- Climate / Region: {climate}
- Current Planting Season: {season}
- Target Crop / Interest: {crop_interest}
- Farm Scale / Area: {farm_size}

Please cover:
1. Feasibility & Recommended Varieties
2. Soil Preparation & Amendments
3. Sowing/Planting Depth and Spacing
4. Key Growth Milestones & Management Tips
"""


def build_pest_diagnosis_prompt(data: dict) -> str:
    """Build a prompt for diagnosing plant diseases and pests."""
    crop = data.get("crop", "Unknown crop")
    affected_parts = data.get("affected_parts", "Leaves/Stems")
    symptoms = data.get("symptoms", "Discoloration/Damage")
    pest_signs = data.get("pest_signs", "None visible")
    preference = data.get("preference", "Integrated (Organic + Chemical)")

    return f"""Please diagnose and provide a treatment plan for the following crop problem:
- Crop / Plant: {crop}
- Affected Plant Parts: {affected_parts}
- Visible Symptoms: {symptoms}
- Pest / Insect Signs: {pest_signs}
- Treatment Preference: {preference}

Please structure your answer as:
1. 🔍 Likely Diagnosis (Primary suspect disease/pest & secondary possibilities)
2. 🌿 Cultural & Organic Solutions (Immediate non-chemical actions)
3. 🧪 Chemical / Conventional Treatments (If applicable, active ingredients and safety warnings)
4. 🛡️ Prevention & Long-Term Management
"""


def build_irrigation_prompt(data: dict) -> str:
    """Build an irrigation schedule and water management prompt."""
    crop = data.get("crop", "General crops")
    soil_type = data.get("soil_type", "Loam")
    irrigation_type = data.get("irrigation_type", "Drip / Sprinkler")
    climate = data.get("climate", "Temperate")
    issue = data.get("issue", "Optimal watering schedule")

    return f"""Please create an Irrigation & Water Management Strategy for:
- Crop & Growth Stage: {crop}
- Soil Texture & Drainage: {soil_type}
- Irrigation System: {irrigation_type}
- Weather / Climate Conditions: {climate}
- Specific Concern / Issue: {issue}

Please include:
1. Optimal Watering Frequency & Depth
2. Critical Watering Stages for this Crop
3. Moisture Monitoring Tips
4. Water Conservation & Salinity Prevention Techniques
"""


def build_fertilizer_prompt(data: dict) -> str:
    """Build a soil nutrition and fertilization recommendation prompt."""
    crop = data.get("crop", "General crop")
    stage = data.get("stage", "Vegetative / Flowering")
    symptoms = data.get("symptoms", "General nutrient schedule")
    fertilizer_pref = data.get("fertilizer_pref", "Balanced NPK + Organic")

    return f"""Please provide a Fertilizer & Soil Nutrition Plan for:
- Crop: {crop}
- Current Growth Stage: {stage}
- Soil Condition / Nutrient Deficiencies: {symptoms}
- Preference: {fertilizer_pref}

Please include:
1. Recommended N-P-K Ratio & Secondary Nutrients (Ca, Mg, S, Micronutrients)
2. Application Method & Timing (Foliar, Soil Drench, Fertigation, Basal)
3. Organic Compost & Manure Recommendations
4. Critical Warnings (Avoiding fertilizer burn, pH considerations)
"""


def build_weather_tips_prompt(data: dict) -> str:
    """Build weather advisory and seasonal tips prompt."""
    climate = data.get("climate", "Temperate")
    season = data.get("season", "Spring/Summer")
    crops = data.get("crops", "Mixed crops")
    event = data.get("event", "General seasonal transition")

    return f"""Provide a Seasonal Farming & Weather Preparedness Guide for:
- Regional Climate: {climate}
- Season / Upcoming Weather Event: {season} - {event}
- Main Crops: {crops}

Please cover:
1. Immediate Risks (e.g. Frost, Heatwaves, Heavy Rains, Drought)
2. Protective Cultural Measures
3. Soil & Canopy Care
4. Seasonal Checklist
"""
