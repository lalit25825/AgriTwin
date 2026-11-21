from __future__ import annotations

import math
import os
from typing import Any

from agritwin_ai.agents.logistics.knowledge import VEHICLE_PROFILES


def optimize_vehicle(
    quantity_tons: float,
    distance_km: float,
    duration_minutes: float,
) -> dict[str, Any]:
    """
    Compare all configured vehicle types and select the best feasible option.

    The optimizer evaluates the total shipment cost, not just vehicle capacity.
    Multi-load shipments are charged for the required number of trips.
    """

    quantity_tons = float(quantity_tons)
    distance_km = float(distance_km)
    duration_minutes = float(duration_minutes)

    if quantity_tons <= 0:
        raise ValueError("quantity_tons must be greater than zero.")

    if distance_km < 0:
        raise ValueError("distance_km cannot be negative.")

    if duration_minutes < 0:
        raise ValueError("duration_minutes cannot be negative.")

    fuel_price = float(
        os.getenv("LOGISTICS_FUEL_PRICE_INR_PER_LITER", "95")
    )

    driver_hour = float(
        os.getenv("LOGISTICS_DRIVER_COST_INR_PER_HOUR", "250")
    )

    handling_per_ton = float(
        os.getenv("LOGISTICS_HANDLING_COST_INR_PER_TON", "150")
    )

    toll_per_trip = float(
        os.getenv("LOGISTICS_ESTIMATED_TOLLS_INR", "0")
    )

    candidates: list[dict[str, Any]] = []

    for vehicle_type, profile in VEHICLE_PROFILES.items():
        capacity_tons = float(profile["capacity_tons"])
        km_per_liter = float(profile["km_per_liter"])

        loads_required = max(
            1,
            math.ceil(quantity_tons / capacity_tons),
        )

        utilization_pct = (
            quantity_tons / (capacity_tons * loads_required)
        ) * 100.0

        fuel_liters_per_trip = distance_km / km_per_liter
        fuel_liters_total = fuel_liters_per_trip * loads_required

        fuel_cost = fuel_liters_total * fuel_price

        driver_cost_per_trip = (
            duration_minutes / 60.0
        ) * driver_hour

        driver_cost_total = driver_cost_per_trip * loads_required

        handling_cost = quantity_tons * handling_per_ton

        toll_cost = toll_per_trip * loads_required

        total_cost = (
            fuel_cost
            + driver_cost_total
            + handling_cost
            + toll_cost
        )

        cost_per_ton = total_cost / quantity_tons

        candidates.append(
            {
                "vehicle_type": vehicle_type,
                "capacity_tons": capacity_tons,
                "km_per_liter": km_per_liter,
                "loads_required": loads_required,
                "capacity_utilization_pct": round(
                    utilization_pct, 2
                ),
                "fuel_liters": round(
                    fuel_liters_total, 2
                ),
                "fuel_cost_inr": round(
                    fuel_cost, 2
                ),
                "driver_cost_inr": round(
                    driver_cost_total, 2
                ),
                "handling_cost_inr": round(
                    handling_cost, 2
                ),
                "tolls_inr": round(
                    toll_cost, 2
                ),
                "estimated_total_inr": round(
                    total_cost, 2
                ),
                "estimated_cost_per_ton_inr": round(
                    cost_per_ton, 2
                ),
            }
        )

    best = min(
        candidates,
        key=lambda candidate: candidate["estimated_total_inr"],
    )

    return {
        "recommended_vehicle": best,
        "candidates": candidates,
        "assumptions": {
            "fuel_price_inr_per_liter": fuel_price,
            "driver_cost_inr_per_hour": driver_hour,
            "handling_cost_inr_per_ton": handling_per_ton,
            "toll_cost_inr_per_trip": toll_per_trip,
            "route_distance_km": distance_km,
            "route_duration_minutes": duration_minutes,
        },
    }


__all__ = ["optimize_vehicle"]