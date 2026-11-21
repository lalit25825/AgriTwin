
from typing import Any, Dict, Optional

from agritwin_ai.memory.models import MemoryItem


class SemanticMemory:
    """Long-lived farmer facts explicitly recorded by the application."""

    def __init__(self) -> None:

        self.memory: Dict[str, MemoryItem] = {}

    def remember(self, key: str, value: Any, source: str = "user", confidence: float = 1.0) -> None:

        self.memory[key] = MemoryItem(
            key=key,
            value=value,
            source=source,
            confidence=confidence
        )

    def recall(self, key: str) -> Optional[MemoryItem]:

        return self.memory.get(key)

    def forget(self, key: str) -> None:

        if key in self.memory:
            del self.memory[key]

    def exists(self, key: str) -> bool:

        return key in self.memory

    def get_all(self) -> Dict[str, MemoryItem]:

        return self.memory
