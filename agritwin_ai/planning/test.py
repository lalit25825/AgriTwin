from agritwin_ai.planning.planner import Planner
from agritwin_ai.understanding.schema import UnderstandingResult


planner = Planner()

understanding = UnderstandingResult(

    intent="harvest_decision",

    entities={},

    missing=[],

    updates={},

    confidence=1.0

)

plan = planner.create_plan(
    understanding
)

print()

print("GOAL")

print(plan.goal)

print()

print("PLAN")

for i, step in enumerate(plan.steps, 1):

    print(f"{i}. {step}")