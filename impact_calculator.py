"""
EcoTransform AI - Environmental Impact Calculator
Calculates landfill diversion, CO2 emissions avoided, and water saved
based on standard EPA WARM lifecycle benchmarks.
"""

# Benchmark Emission Factors (kg CO2-equivalent avoided per kg of waste recycled/reused)
# Source: US EPA Waste Reduction Model (WARM) averages
CARBON_FACTORS = {
    "aluminum": 9.10,
    "steel": 1.80,
    "metal": 4.50,
    "plastic": 2.15,
    "pet": 2.20,
    "hdpe": 1.95,
    "glass": 0.62,
    "paper": 1.38,
    "cardboard": 1.45,
    "organic": 0.52,  # Methane avoidance from aerobic diversion
    "food": 0.50,
    "textile": 3.80,
    "wood": 1.20,
    "electronic": 12.50,
    "battery": 8.00,
    "default": 1.20
}

# Water footprint factor (Liters saved per kg of material diverted/reused)
WATER_FACTORS = {
    "paper": 26.0,
    "cardboard": 20.0,
    "textile": 60.0,
    "plastic": 12.0,
    "aluminum": 40.0,
    "glass": 4.0,
    "default": 10.0
}

# Standard archetype weights (in kg) if not provided by model
ARCHETYPE_WEIGHTS = {
    "plastic bottle": 0.025,
    "soda can": 0.015,
    "glass bottle": 0.400,
    "glass jar": 0.250,
    "cardboard box": 0.180,
    "paper cup": 0.012,
    "newspaper": 0.080,
    "battery": 0.045,
    "electronic": 0.350,
    "food waste": 0.150,
    "default": 0.050
}

def estimate_archetype_weight(item_name: str, material: str) -> float:
    """Estimates typical physical weight in kg based on item name and material."""
    name_lower = (item_name + " " + material).lower()
    for key, weight in ARCHETYPE_WEIGHTS.items():
        if key in name_lower:
            return weight
    return ARCHETYPE_WEIGHTS["default"]

def calculate_environmental_impact(item_name: str, primary_material: str, detected_weight_kg: float = None):
    """
    Computes environmental metrics:
    - Landfill diverted (kg)
    - CO2e avoided (kg)
    - Water conserved (liters)
    """
    material_lower = primary_material.lower()

    # Determine weight
    if detected_weight_kg and detected_weight_kg > 0.001:
        weight_kg = detected_weight_kg
    else:
        weight_kg = estimate_archetype_weight(item_name, primary_material)

    # Determine carbon factor
    carbon_factor = CARBON_FACTORS["default"]
    for key, factor in CARBON_FACTORS.items():
        if key in material_lower:
            carbon_factor = factor
            break

    # Determine water factor
    water_factor = WATER_FACTORS["default"]
    for key, factor in WATER_FACTORS.items():
        if key in material_lower:
            water_factor = factor
            break

    co2_avoided = round(weight_kg * carbon_factor, 4)
    water_saved = round(weight_kg * water_factor, 2)
    landfill_diverted = round(weight_kg, 4)

    return {
        "estimated_weight_kg": weight_kg,
        "co2_avoided_kg": co2_avoided,
        "water_saved_liters": water_saved,
        "landfill_diverted_kg": landfill_diverted,
        "benchmarking_note": "Derived from EPA Waste Reduction Model (WARM) lifecycle conversion factors."
    }
