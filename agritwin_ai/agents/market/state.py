from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MarketState:
    """
    Transient state for one Market Agent request.

    The workflow stores:
    - information extracted from the user request
    - market tool observations
    - deterministic market analysis
    - final deterministic decision

    The workflow itself does not make market decisions.
    """

    commodity: str | None = None
    market: str | None = None
    state: str | None = None
    district: str | None = None

    date: str | None = None
    horizon: int | None = None

    current_price: float | None = None

    market_data: dict[str, Any] | None = None
    forecast: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    economics: dict[str, Any] | None = None

    decision: dict[str, Any] | None = None

    completed: bool = False