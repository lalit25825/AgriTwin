

from dataclasses import dataclass, field
from typing import Any, Dict
from datetime import datetime


@dataclass
class MemoryItem:
    """
    Represents a single fact remembered by AgriTwin.
    """

    key: str
    value: Any

    # Where this fact came from
    source: str = "user"

    # Confidence assigned to this fact
    confidence: float = 1.0

    # Last updated time
    updated_at: datetime = field(default_factory=datetime.now)