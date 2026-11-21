from agritwin_ai.planning.plans.harvest import HARVEST_PLAN
from agritwin_ai.planning.plans.market import MARKET_PLAN
from agritwin_ai.planning.plans.disease import DISEASE_PLAN


PLAN_REGISTRY = {

    "harvest_decision": HARVEST_PLAN,

    "market_price": MARKET_PLAN,

    "disease_detection": DISEASE_PLAN

}