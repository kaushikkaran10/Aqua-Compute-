# Illustrative assumptions for environmental footprint calculations
ENERGY_PER_1K_TOKENS = {
    "small": 0.002,
    "medium": 0.006,
    "large": 0.012,
}
WUE = 0.8  # Direct water usage effectiveness (L/kWh)
PUE = 1.2  # Power usage effectiveness
GRID_WATER = 1.5  # Indirect water intensity of power grid (L/kWh)
GRID_CARBON = 700.0  # Grid carbon intensity (g CO2/kWh)


def estimate(tier: str, input_tokens: int, output_tokens: int, region: str = "IN") -> dict:
    """Estimate energy consumption, direct/indirect water usage, and carbon emissions."""
    energy_factor = ENERGY_PER_1K_TOKENS.get(tier, ENERGY_PER_1K_TOKENS["small"])
    energy_kwh = (input_tokens + output_tokens) / 1000.0 * energy_factor
    direct_water_l = energy_kwh * WUE
    indirect_water_l = energy_kwh * PUE * GRID_WATER
    water_l = direct_water_l + indirect_water_l
    carbon_g = energy_kwh * PUE * GRID_CARBON

    return {
        "energy_kwh": round(energy_kwh, 6),
        "direct_water_l": round(direct_water_l, 6),
        "indirect_water_l": round(indirect_water_l, 6),
        "water_l": round(water_l, 6),
        "carbon_g": round(carbon_g, 4),
        "basis": "placeholder",
    }
