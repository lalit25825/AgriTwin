"""Authenticated chat API for the uploaded AgriTwin multi-agent runtime."""

from __future__ import annotations

import logging
import math
import os
import re
import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from agritwin_ai.config.settings import GROQ_API_KEY
from agritwin_ai.web.session_manager import session_manager
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_active_user

LOGGER = logging.getLogger("agritwin.ai_chat")
router = APIRouter(prefix="/ai", tags=["AgriTwin AI assistant"])

AgentName = Literal["coordinator", "harvest", "climate", "market", "logistics"]

ROLE_CONTEXT: dict[str, dict[str, str]] = {
    "farmer": {
        "label": "Farmer",
        "priorities": "crop health, crop-stage decisions, harvest timing, weather risk, post-harvest loss, mandi options, net realization and practical farm-level actions",
    },
    "driver": {
        "label": "Driver / vehicle owner",
        "priorities": "shipment details, pickup and drop locations, route feasibility, load capacity, trip duration, estimated transport costs, safe movement and vehicle utilization",
    },
    "transporter": {
        "label": "Transporter",
        "priorities": "shipment planning, fleet and load suitability, route feasibility, turnaround time, estimated costs and delivery coordination",
    },
    "storage_owner": {
        "label": "Storage owner",
        "priorities": "commodity-specific storage conditions, incoming and outgoing inventory, storage duration, spoilage risk, weather exposure, movement cost and commercial utilization",
    },
    "storage_provider": {
        "label": "Storage provider",
        "priorities": "commodity-specific storage conditions, incoming and outgoing inventory, storage duration, spoilage risk, weather exposure, movement cost and commercial utilization",
    },
    "mandi_seller": {
        "label": "Mandi seller / trader",
        "priorities": "commodity sourcing, mandi observations, quote dates and freshness, grade and quality, nearby market comparisons, buying decisions, selling margins and transport economics",
    },
    "buyer": {
        "label": "Buyer",
        "priorities": "commodity sourcing, availability, quality and grade, market observations, purchasing economics, transport feasibility and reliable supply",
    },
    "mandi_owner": {
        "label": "Mandi owner / operator",
        "priorities": "market arrivals, commodity mix, arrival and dispatch coordination, market-level price observations, yard movement and operational planning",
    },
    "fpo_manager": {
        "label": "FPO manager",
        "priorities": "member-level crop aggregation, harvest windows, bulk quantity planning, collective logistics, storage coordination, mandi access and buyer linkages",
    },
    "fpo": {
        "label": "FPO manager",
        "priorities": "member-level crop aggregation, harvest windows, bulk quantity planning, collective logistics, storage coordination, mandi access and buyer linkages",
    },
    "admin": {
        "label": "Platform administrator",
        "priorities": "supply-chain coordination, service reliability, transparent market information, data quality and responsible platform operations",
    },
}

ACTIVE_AGENTS = [
    {
        "id": "coordinator",
        "name": "AgriTwin Coordinator",
        "kind": "orchestrator",
        "description": "Understands the full request, selects relevant specialists and combines their results.",
        "capabilities": ["Automatic routing", "Multi-agent coordination", "Evidence-based synthesis"],
        "selectable": True,
    },
    {
        "id": "harvest",
        "name": "Harvest Agent",
        "kind": "specialist",
        "description": "Uses crop knowledge and weather observations to assess harvest readiness and timing.",
        "capabilities": ["Crop knowledge", "Harvest decisions", "Harvest-weather checks"],
        "selectable": True,
    },
    {
        "id": "climate",
        "name": "Climate Agent",
        "kind": "specialist",
        "description": "Retrieves current conditions and multi-day weather forecasts using Open-Meteo.",
        "capabilities": ["Current weather", "Forecasts", "Rain, temperature and wind risk"],
        "selectable": True,
    },
    {
        "id": "market",
        "name": "Market Agent",
        "kind": "specialist",
        "description": "Analyses OGD / AGMARKNET observations, nearby mandis, historical market data and labelled price outlooks.",
        "capabilities": ["Mandi observations", "Nearby market discovery", "Price history", "Forecast and sale decision support"],
        "selectable": True,
    },
    {
        "id": "logistics",
        "name": "Logistics Agent",
        "kind": "specialist",
        "description": "Plans agricultural shipments using geocoding, road routing, vehicle suitability, cost estimates and logistics risk.",
        "capabilities": ["Route planning", "Vehicle optimization", "Estimated transport cost", "Logistics risk"],
        "selectable": True,
    },
]

PLANNED_AGENTS = [
    {
        "id": "storage",
        "name": "Storage Agent",
        "status": "planned",
        "note": "Storage knowledge and decision utilities exist in the supplied source, but there is no standalone Storage Agent connected to its Coordinator.",
    },
    {
        "id": "equity",
        "name": "Equity Agent",
        "status": "not_in_uploaded_runtime",
        "note": "A standalone Equity Agent implementation was not present in the supplied multi-agent ZIP.",
    },
    {
        "id": "disease",
        "name": "Disease Agent",
        "status": "placeholder",
        "note": "The supplied source contains a package placeholder, not an end-to-end disease diagnosis workflow.",
    },
]


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    session_id: str | None = Field(default=None, min_length=8, max_length=80)
    agent: AgentName = "coordinator"


class AIChatResponse(BaseModel):
    session_id: str
    agent: str
    agent_label: str
    stakeholder_role: str
    agents_used: list[str]
    response: Any
    observations: dict[str, Any] = Field(default_factory=dict)


def _safe_json(value: Any) -> Any:
    """Convert agent outputs (including pandas/numpy values) to JSON-safe data."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if hasattr(value, "model_dump"):
        return _safe_json(value.model_dump())
    if hasattr(value, "to_dict"):
        try:
            return _safe_json(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            return _safe_json(value.tolist())
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return _safe_json(value.item())
        except Exception:
            pass
    return str(value)


def _provider_is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or GROQ_API_KEY)


@router.get("/health")
async def ai_health(current_user: User = Depends(get_current_active_user)) -> dict[str, Any]:
    """Return safe provider state; never return credentials."""
    configured = _provider_is_configured()
    return {
        "status": "ready" if configured else "setup_required",
        "provider": "Groq (OpenAI-compatible API)",
        "provider_configured": configured,
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        "active_specialists": 4,
        "stakeholder_role": getattr(current_user.role, "value", str(current_user.role)),
    }


@router.get("/agents")
async def list_ai_agents(current_user: User = Depends(get_current_active_user)) -> dict[str, Any]:
    """List active and planned agents. Active agents are available to every role."""
    role_value = getattr(current_user.role, "value", str(current_user.role))
    return {
        "agents": ACTIVE_AGENTS,
        "planned_agents": PLANNED_AGENTS,
        "all_active_agents_available_to_role": role_value,
        "access_policy": "Every authenticated stakeholder can use the Coordinator and any active specialist.",
    }


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_agents(
    request: AIChatRequest,
    current_user: User = Depends(get_current_active_user),
) -> AIChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Please enter a message.")
    if not _provider_is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI chat is not configured yet. Add a newly generated GROQ_API_KEY to your project .env file and restart AgriTwin.",
        )

    client_session_id = (request.session_id or uuid.uuid4().hex).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", client_session_id):
        raise HTTPException(status_code=422, detail="Invalid conversation session identifier.")

    role_value = getattr(current_user.role, "value", str(current_user.role))
    role_info = ROLE_CONTEXT.get(role_value, ROLE_CONTEXT["admin"])
    stakeholder_context = (
        f"Authenticated stakeholder role: {role_info['label']}.\n"
        f"Role-specific priorities: {role_info['priorities']}.\n"
        "All active agents are available to this stakeholder. Do not restrict specialist access by role. "
        "Adapt examples, terminology and practical recommendations to this stakeholder's work. "
        "Do not assume the user's farm, vehicle, storage facility, inventory, location or commercial terms "
        "unless they are supplied in the conversation."
    )

    # The client session id is scoped to the authenticated account and role.
    # A guessed or copied browser id cannot attach to another stakeholder's memory.
    user_key = str(current_user.id).replace("-", "")
    runtime_session_id = f"user-{user_key}-{role_value}-{client_session_id}"

    try:
        runtime = session_manager.get(runtime_session_id, stakeholder_context=stakeholder_context)
        result, agents_used, observations = await run_in_threadpool(
            runtime.run,
            request.agent,
            message,
        )
    except RuntimeError as exc:
        LOGGER.exception("AgriTwin multi-agent runtime/provider error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Unexpected AgriTwin chat failure")
        raise HTTPException(
            status_code=500,
            detail="AgriTwin could not complete this request. Check the server terminal for diagnostic details.",
        ) from exc

    labels = {
        "coordinator": "AgriTwin Coordinator",
        "harvest": "Harvest Agent",
        "climate": "Climate Agent",
        "market": "Market Agent",
        "logistics": "Logistics Agent",
    }
    return AIChatResponse(
        session_id=client_session_id,
        agent=request.agent,
        agent_label=labels[request.agent],
        stakeholder_role=role_info["label"],
        agents_used=list(agents_used or []),
        response=_safe_json(result),
        observations=_safe_json(observations or {}),
    )
