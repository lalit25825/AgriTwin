from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MarketDecision:
    """
    Deterministic market decision produced from current price,
    forecast trajectory, volatility, and market context.
    """

    action: str
    confidence: float
    expected_price_change_pct: float
    current_price: float
    forecast_price: float
    reasons: list[str]
    risk_level: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "confidence": self.confidence,
            "expected_price_change_pct": (
                self.expected_price_change_pct
            ),
            "current_price": self.current_price,
            "forecast_price": self.forecast_price,
            "reasons": self.reasons,
            "risk_level": self.risk_level,
        }


class MarketDecisionEngine:
    """
    Converts a market forecast into an actionable decision.

    Actions:
        SELL
        HOLD
        STORE
        REDIRECT

    V1 is intentionally deterministic. No LLM is allowed to override
    the numerical decision.
    """

    ACTIONS = {
        "SELL",
        "HOLD",
        "STORE",
        "REDIRECT",
    }

    def decide(
        self,
        current_price: float,
        forecast_prices: list[float],
        volatility_pct: float = 0.0,
        storage_available: bool = False,
        nearby_market_advantage_pct: float = 0.0,
    ) -> MarketDecision:
        self._validate_inputs(
            current_price=current_price,
            forecast_prices=forecast_prices,
            volatility_pct=volatility_pct,
            nearby_market_advantage_pct=(
                nearby_market_advantage_pct
            ),
        )

        forecast_price = float(
            forecast_prices[-1]
        )

        expected_change_pct = (
            (
                forecast_price
                - current_price
            )
            / current_price
        ) * 100

        reasons: list[str] = []

        # ---------------------------------------------------------
        # REDIRECT
        # ---------------------------------------------------------

        if nearby_market_advantage_pct >= 10:
            reasons.append(
                "NEARBY_MARKET_HAS_SIGNIFICANTLY_HIGHER_PRICE"
            )

            confidence = self._calculate_confidence(
                expected_change_pct=expected_change_pct,
                volatility_pct=volatility_pct,
                bonus=0.10,
            )

            return MarketDecision(
                action="REDIRECT",
                confidence=confidence,
                expected_price_change_pct=(
                    expected_change_pct
                ),
                current_price=current_price,
                forecast_price=forecast_price,
                reasons=reasons,
                risk_level=self._risk_level(
                    volatility_pct
                ),
            )

        # ---------------------------------------------------------
        # STORE
        # ---------------------------------------------------------

        if (
            storage_available
            and expected_change_pct >= 8
        ):
            reasons.append(
                "FORECAST_INDICATES_STRONG_PRICE_INCREASE"
            )

            reasons.append(
                "STORAGE_AVAILABLE"
            )

            confidence = self._calculate_confidence(
                expected_change_pct=expected_change_pct,
                volatility_pct=volatility_pct,
                bonus=0.05,
            )

            return MarketDecision(
                action="STORE",
                confidence=confidence,
                expected_price_change_pct=(
                    expected_change_pct
                ),
                current_price=current_price,
                forecast_price=forecast_price,
                reasons=reasons,
                risk_level=self._risk_level(
                    volatility_pct
                ),
            )

        # ---------------------------------------------------------
        # SELL
        # ---------------------------------------------------------

        if expected_change_pct <= -5:
            reasons.append(
                "FORECAST_INDICATES_PRICE_DECLINE"
            )

            confidence = self._calculate_confidence(
                expected_change_pct=expected_change_pct,
                volatility_pct=volatility_pct,
                bonus=0.05,
            )

            return MarketDecision(
                action="SELL",
                confidence=confidence,
                expected_price_change_pct=(
                    expected_change_pct
                ),
                current_price=current_price,
                forecast_price=forecast_price,
                reasons=reasons,
                risk_level=self._risk_level(
                    volatility_pct
                ),
            )

        # ---------------------------------------------------------
        # HOLD
        # ---------------------------------------------------------

        if expected_change_pct >= 3:
            reasons.append(
                "MODERATE_UPWARD_PRICE_TREND"
            )
        elif expected_change_pct <= -3:
            reasons.append(
                "MODERATE_DOWNWARD_PRICE_TREND"
            )
        else:
            reasons.append(
                "PRICE_EXPECTED_TO_REMAIN_RELATIVELY_STABLE"
            )

        confidence = self._calculate_confidence(
            expected_change_pct=expected_change_pct,
            volatility_pct=volatility_pct,
        )

        return MarketDecision(
            action="HOLD",
            confidence=confidence,
            expected_price_change_pct=(
                expected_change_pct
            ),
            current_price=current_price,
            forecast_price=forecast_price,
            reasons=reasons,
            risk_level=self._risk_level(
                volatility_pct
            ),
        )

    @staticmethod
    def _validate_inputs(
        current_price: float,
        forecast_prices: list[float],
        volatility_pct: float,
        nearby_market_advantage_pct: float,
    ) -> None:
        if current_price <= 0:
            raise ValueError(
                "current_price must be positive."
            )

        if not forecast_prices:
            raise ValueError(
                "forecast_prices cannot be empty."
            )

        if any(
            price < 0
            for price in forecast_prices
        ):
            raise ValueError(
                "forecast prices cannot be negative."
            )

        if volatility_pct < 0:
            raise ValueError(
                "volatility_pct cannot be negative."
            )

        if nearby_market_advantage_pct < 0:
            raise ValueError(
                "nearby_market_advantage_pct "
                "cannot be negative."
            )

    @staticmethod
    def _calculate_confidence(
        expected_change_pct: float,
        volatility_pct: float,
        bonus: float = 0.0,
    ) -> float:
        """
        Produces a bounded deterministic confidence score.

        Stronger price signals increase confidence.
        Higher volatility reduces confidence.
        """

        signal_strength = min(
            abs(expected_change_pct) / 20,
            1.0,
        )

        volatility_penalty = min(
            volatility_pct / 30,
            0.5,
        )

        confidence = (
            0.55
            + (signal_strength * 0.30)
            + bonus
            - volatility_penalty
        )

        return round(
            max(
                0.0,
                min(confidence, 0.95),
            ),
            3,
        )

    @staticmethod
    def _risk_level(
        volatility_pct: float,
    ) -> str:
        if volatility_pct >= 20:
            return "HIGH"

        if volatility_pct >= 10:
            return "MEDIUM"

        return "LOW"