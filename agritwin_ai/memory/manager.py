from agritwin_ai.memory.working_memory import WorkingMemory
from agritwin_ai.memory.semantic_memory import SemanticMemory
from agritwin_ai.memory.episodic_memory import EpisodicMemory
from typing import Any, Optional


class MemoryManager:
    """Facade over working, semantic, and episodic memory stores."""

    def __init__(self) -> None:

        self.working = WorkingMemory()

        self.semantic = SemanticMemory()

        self.episodic = EpisodicMemory()

    # ------------------------
    # Working Memory
    # ------------------------

    def update_working(self, updates: dict[str, Any]) -> None:

        self.working.update_from_dict(updates)

    def get_working(self) -> dict[str, Any]:

        return self.working.get_all()

    # ------------------------
    # Semantic Memory
    # ------------------------

    def remember_fact(self, key: str, value: Any) -> None:

        self.semantic.remember(key, value)

    def recall_fact(self, key: str) -> Optional[Any]:

        return self.semantic.recall(key)

    # ------------------------
    # Episodic Memory
    # ------------------------

    def remember_event(self, event: str, data: dict[str, Any]) -> None:

        self.episodic.remember(event, data)

    def get_last_event(self) -> Optional[Any]:

        return self.episodic.get_last()

    # ------------------------
    # Reset
    # ------------------------

    def clear_working_memory(self) -> None:

        self.working.clear()
