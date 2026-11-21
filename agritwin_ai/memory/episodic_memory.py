
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class Episode:
    """A timestamped notable event from a farmer interaction."""

    event: str

    data: Dict[str, Any]

    timestamp: datetime = field(default_factory=datetime.now)


class EpisodicMemory:
    """Append-only in-memory history of notable agent events."""

    def __init__(self) -> None:

        self.episodes: List[Episode] = []

    def remember(self, event: str, data: Dict[str, Any]) -> None:

        self.episodes.append(
            Episode(
                event=event,
                data=data
            )
        )

    def get_last(self) -> Episode | None:

        if not self.episodes:
            return None

        return self.episodes[-1]

    def get_all(self) -> List[Episode]:

        return self.episodes

    def clear(self) -> None:

        self.episodes.clear()
