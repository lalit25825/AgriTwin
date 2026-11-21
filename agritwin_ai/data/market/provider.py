from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class MarketDataProvider(ABC):
    """
    Abstract interface for agricultural market-data providers.

    Concrete providers such as the Government OGD/DMI provider,
    Agmarknet provider, or e-NAM provider must implement this interface.

    The rest of AgriTwin must depend on this interface rather than
    provider-specific API details.
    """

    name: str = "unknown"

    @abstractmethod
    def fetch_latest(self) -> list[dict[str, Any]]:
        """
        Fetch the latest available market observations.

        Returns raw provider records.
        Normalization happens outside the provider.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_range(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        Fetch market observations for an inclusive date range.

        Parameters
        ----------
        start_date:
            First requested date.

        end_date:
            Last requested date.

        Returns
        -------
        list[dict[str, Any]]
            Raw provider records.
        """
        raise NotImplementedError

    def health_check(self) -> bool:
        """
        Check whether the provider is currently reachable.

        Providers may override this when they support an inexpensive
        health endpoint.
        """
        return True