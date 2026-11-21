from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class MarketRequest:
    commodity: str
    market: str
    horizon: int = 7
    markets: tuple[str, ...] = ()


class MarketRequestParser:
    """
    Lightweight parser for Coordinator-facing market requests.

    V1 intentionally supports explicit commodity and market names.
    Semantic interpretation can later be delegated to the existing
    Understanding Layer.
    """

    COMMON_COMMODITIES = {
        "onion": "Onion",
        "onions": "Onion",
        "tomato": "Tomato",
        "tomatoes": "Tomato",
        "potato": "Potato",
        "potatoes": "Potato",
        "wheat": "Wheat",
        "rice": "Rice",
        "maize": "Maize",
        "cotton": "Cotton",
        "soybean": "Soybean",
        "sugarcane": "Sugarcane",
        "grapes": "Grapes",
    }

    def parse(
        self,
        user_message: str,
    ) -> MarketRequest:
        if not user_message or not user_message.strip():
            raise ValueError(
                "Market request cannot be empty."
            )

        text = user_message.strip()

        commodity = self._extract_commodity(
            text
        )

        markets = self._extract_markets(text)
        market = markets[0] if markets else None

        horizon = self._extract_horizon(
            text
        )

        if commodity is None:
            raise ValueError(
                "Could not identify commodity. "
                "Specify a commodity such as Onion."
            )

        if market is None:
            raise ValueError(
                "Could not identify market. "
                "Specify a mandi/market such as Lasalgaon."
            )

        return MarketRequest(
            commodity=commodity,
            market=market,
            horizon=horizon,
            markets=tuple(markets),
        )

    def _extract_commodity(self, text: str) -> str | None:
        import re

        lowered = text.lower()

        for key, value in self.COMMON_COMMODITIES.items():
            pattern = rf"\b{re.escape(key)}\b"

            if re.search(pattern, lowered):
                return value

        return None

    @classmethod
    def _extract_markets(cls, text: str) -> list[str]:
        import re

        lowered = text.lower()
        known_markets = {
            "lasalgaon": "Lasalgaon",
            "lasangaon": "Lasalgaon",
            "nashik": "Nashik",
            "pune": "Pune",
            "mumbai": "Mumbai",
            "manmad": "Manmad",
            "nagpur": "Nagpur",
            "akola": "Akola",
            "sangli": "Sangli",
            "kolhapur": "Kolhapur",
        }
        matches: list[tuple[int, str]] = []
        for key, value in known_markets.items():
            match = re.search(rf"\b{re.escape(key)}\b", lowered)
            if match:
                matches.append((match.start(), value))

        # Keep user-mentioned order and remove duplicate aliases.
        ordered: list[str] = []
        for _, market in sorted(matches, key=lambda item: item[0]):
            if market not in ordered:
                ordered.append(market)
        return ordered

    @classmethod
    def _extract_market(cls, text: str) -> str | None:
        markets = cls._extract_markets(text)
        return markets[0] if markets else None

    @staticmethod
    def _extract_horizon(text: str) -> int:
        import re

        lowered = text.lower()

        if ("next week" in lowered and any(term in lowered for term in ("week after", "following week", "after that week"))):
            return 14

        match = re.search(r"(\d+)\s*(?:day|days)", lowered)
        if match:
            horizon = int(match.group(1))
            if horizon <= 0:
                raise ValueError("Forecast horizon must be positive.")
            if horizon > 30:
                raise ValueError("Forecast horizon cannot exceed 30 days.")
            return horizon

        # Interpret explicit "up to 25 Nov 2026" requests as a horizon.
        date_match = re.search(
            r"(?:up\s*to|until|through|till)\s+(\d{1,2})\s+([a-z]+)\s+(\d{4})",
            lowered,
        )
        if date_match:
            day, month_name, year = date_match.groups()
            try:
                target = datetime.strptime(
                    f"{day} {month_name} {year}", "%d %B %Y"
                ).date()
            except ValueError:
                try:
                    target = datetime.strptime(
                        f"{day} {month_name} {year}", "%d %b %Y"
                    ).date()
                except ValueError as exc:
                    raise ValueError("Could not parse the requested forecast end date.") from exc
            horizon = (target - date.today()).days
            if horizon <= 0:
                raise ValueError("The forecast end date must be in the future.")
            if horizon > 30:
                raise ValueError("Forecast horizon cannot exceed 30 days.")
            return horizon

        return 7

