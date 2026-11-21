from fastapi import APIRouter, Depends
from backend.app.agents.orchestrator import get_agent_status, run_agent_team
from backend.app.agents.schemas import AgentRunRequest
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_active_user

router = APIRouter(prefix="/agents", tags=["Multi-agent system"])


@router.get("/status")
async def agents_status():
    return {"agents": get_agent_status()}


@router.post("/run")
async def run_agents(
    request: AgentRunRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Run the AgriTwin specialist-agent team for an authenticated user."""
    return await run_agent_team(request)
