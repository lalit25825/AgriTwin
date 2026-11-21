from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LogisticsState:
    # Shipment
    commodity: Optional[str] = None
    quantity_tons: Optional[float] = None

    # Locations
    origin: Optional[str] = None
    destination: Optional[str] = None
    market: Optional[str] = None

    # Coordinates
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None

    # Routing
    distance_km: Optional[float] = None
    duration_minutes: Optional[float] = None
    route: Optional[Dict[str, Any]] = None
    alternative_routes: List[Dict[str, Any]] = field(default_factory=list)

    # Weather
    origin_weather: Optional[Dict[str, Any]] = None
    destination_weather: Optional[Dict[str, Any]] = None

    # Transport
    vehicle_type: Optional[str] = None
    vehicle_capacity_tons: Optional[float] = None
    vehicle_loads_required: Optional[int] = None
    vehicle_utilization_pct: Optional[float] = None
    vehicle_optimization: Optional[Dict[str, Any]] = None

    # Cost
    fuel_cost: Optional[float] = None
    toll_cost: Optional[float] = None
    driver_cost: Optional[float] = None
    loading_cost: Optional[float] = None
    unloading_cost: Optional[float] = None
    transport_cost: Optional[float] = None
    cost_per_ton: Optional[float] = None
    total_cost: Optional[float] = None

    # Agricultural logistics risk
    spoilage_risk: Optional[str] = None
    weather_risk: Optional[str] = None
    logistics_risk: Optional[str] = None

    # Market economics
    market_price: Optional[float] = None
    expected_revenue: Optional[float] = None
    expected_net_realization: Optional[float] = None

    # Final deterministic decision
    decision: Optional[Dict[str, Any]] = None

    # Provenance
    data_sources: Dict[str, Any] = field(default_factory=dict)

    # Errors
    errors: List[str] = field(default_factory=list)