
from typing import Any, Dict, Optional

from agritwin_ai.memory.models import MemoryItem


class WorkingMemory:
    """Short-lived, editable facts for the active farmer context."""

    def __init__(self) -> None:

        self.memory: Dict[str, MemoryItem] = {}

    def set(self, key: str, value: Any, source: str = "user", confidence: float = 1.0) -> None:

        self.memory[key] = MemoryItem(
            key=key,
            value=value,
            source=source,
            confidence=confidence
        )

    def get(self, key: str) -> Optional[MemoryItem]:

        return self.memory.get(key)

    def exists(self, key: str) -> bool:

        return key in self.memory

    def delete(self, key: str) -> None:

        if key in self.memory:
            del self.memory[key]

    def clear(self) -> None:

        self.memory.clear()

    def get_all(self) -> Dict[str, MemoryItem]:

        return self.memory

    def update_from_dict(
        self,
        updates: Dict[str, Any],
        source: str = "user",
        confidence: float = 1.0,
    ) -> None:

        for key, value in updates.items():

            self.set(
                key,
                value,
                source,
                confidence
            )
