from __future__ import annotations

from typing import Any

# These are deliberately conservative engineering heuristics, not crop-science
# guarantees. They are configuration points so the project can later replace
# them with validated domain data.
CROP_LOGISTICS_PROFILES: dict[str, dict[str, Any]] = {
    "onion": {
        "aliases": ["onion", "onions", "kanda", "pyaj", "pyaaz"],
        "handling_loss_pct": 1.5,
        "temperature_min_c": 5.0,
        "temperature_max_c": 30.0,
        "rain_sensitivity": 0.65,
        "perishable": True,
    },
    "potato": {
        "aliases": ["potato", "potatoes", "aloo"],
        "handling_loss_pct": 2.0,
        "temperature_min_c": 4.0,
        "temperature_max_c": 25.0,
        "rain_sensitivity": 0.55,
        "perishable": True,
    },
    "tomato": {
        "aliases": ["tomato", "tomatoes"],
        "handling_loss_pct": 3.0,
        "temperature_min_c": 8.0,
        "temperature_max_c": 28.0,
        "rain_sensitivity": 0.80,
        "perishable": True,
    },
    "wheat": {
        "aliases": ["wheat", "gehun", "gahu"],
        "handling_loss_pct": 0.5,
        "temperature_min_c": 0.0,
        "temperature_max_c": 40.0,
        "rain_sensitivity": 0.25,
        "perishable": False,
    },
    "rice": {
        "aliases": ["rice", "paddy", "dhan"],
        "handling_loss_pct": 0.5,
        "temperature_min_c": 0.0,
        "temperature_max_c": 40.0,
        "rain_sensitivity": 0.30,
        "perishable": False,
    },
}

DEFAULT_PROFILE = {
    "handling_loss_pct": 1.0,
    "temperature_min_c": 5.0,
    "temperature_max_c": 35.0,
    "rain_sensitivity": 0.50,
    "perishable": True,
}

VEHICLE_PROFILES: dict[str, dict[str, float]] = {
    "mini_truck": {"capacity_tons": 2.0, "km_per_liter": 9.0},
    "light_truck": {"capacity_tons": 5.0, "km_per_liter": 6.5},
    "medium_truck": {"capacity_tons": 10.0, "km_per_liter": 4.5},
    "heavy_truck": {"capacity_tons": 20.0, "km_per_liter": 3.0},
}


def normalize_commodity(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    for canonical, profile in CROP_LOGISTICS_PROFILES.items():
        if lowered == canonical or lowered in profile["aliases"]:
            return canonical
    return lowered


def profile_for(commodity: str | None) -> dict[str, Any]:
    normalized = normalize_commodity(commodity)
    return CROP_LOGISTICS_PROFILES.get(normalized or "", DEFAULT_PROFILE.copy())


def select_vehicle(quantity_tons: float) -> tuple[str, dict[str, float]]:
    if quantity_tons <= 2:
        name = "mini_truck"
    elif quantity_tons <= 5:
        name = "light_truck"
    elif quantity_tons <= 10:
        name = "medium_truck"
    else:
        name = "heavy_truck"
    return name, VEHICLE_PROFILES[name]
