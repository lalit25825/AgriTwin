
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class UnderstandingResult:
    """
    Standard output of the Understanding Layer.
    Every user message must be converted into this format.
    """

    # What the user wants
    intent: str

    # Extracted structured entities
    entities: Dict[str, Any] = field(default_factory=dict)

    # Information still required
    missing: List[str] = field(default_factory=list)

    # Facts discovered from this message
    updates: Dict[str, Any] = field(default_factory=dict)

    # Confidence score (0.0 - 1.0)
    confidence: float = 0.0