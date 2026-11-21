from dataclasses import dataclass, field
from typing import List

from agritwin_ai.planning.registry import PLAN_REGISTRY


@dataclass
class Plan:

    goal: str

    steps: List[str] = field(default_factory=list)


class Planner:

    def create_plan(self, understanding):

        steps = PLAN_REGISTRY.get(

            understanding.intent,

            ["Answer directly"]

        )

        return Plan(

            goal=understanding.intent,

            steps=steps

        )