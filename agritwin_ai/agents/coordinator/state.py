from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CoordinatorState:

    user_request: Optional[str] = None

    required_agents: list[str] = field(default_factory=list)

    completed_agents: list[str] = field(default_factory=list)

    agent_outputs: Dict[str, Any] = field(default_factory=dict)

    final_answer: Optional[str] = None

    decision: Optional[Dict[str, Any]] = None

    completed: bool = False