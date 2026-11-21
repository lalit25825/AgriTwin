"""FastAPI application that exposes the AgriTwin multi-agent runtime and UI."""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agritwin_ai.config.settings import GROQ_API_KEY
from agritwin_ai.agents.market.market_runtime import MarketRuntime
from agritwin_ai.web.session_manager import session_manager


LOGGER = logging.getLogger("agritwin.web")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
MARKET_DATA_PATH = PROJECT_ROOT / "data" / "market" / "processed" / "market_records.csv"
MARKET_RUNTIME = MarketRuntime(data_path=MARKET_DATA_PATH)

AgentName = Literal["coordinator", "harvest", "climate", "market", "logistics"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    session_id: str | None = Field(default=None, max_length=80)
    agent: AgentName = "coordinator"


class ChatResponse(BaseModel):
    session_id: str
    agent: str
    agent_label: str
    agents_used: list[str]
    response: Any
    observations: dict[str, Any] = Field(default_factory=dict)


def _safe_json(value: Any) -> Any:
    """Convert numpy/pandas/date/dataclass-like values into JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
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


def _market_snapshot() -> dict[str, Any]:
    if not MARKET_DATA_PATH.exists():
        return {"available": False, "records": 0, "snapshot_date": None}
    try:
        frame = pd.read_csv(MARKET_DATA_PATH, usecols=["date", "commodity", "market"])
        dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
        return {
            "available": not frame.empty,
            "records": int(len(frame)),
            "commodities": int(frame["commodity"].nunique()),
            "markets": int(frame["market"].nunique()),
            "snapshot_date": dates.max().date().isoformat() if not dates.empty else None,
            "source": "OGD / AGMARKNET snapshot",
        }
    except Exception as exc:
        LOGGER.warning("Unable to read market snapshot metadata: %s", exc)
        return {"available": False, "records": 0, "snapshot_date": None}


AGENTS = [
    {
        "id": "coordinator",
        "name": "Coordinator",
        "type": "Orchestration",
        "status": "active",
        "description": "Understands the request, delegates to specialists and combines their findings.",
        "capabilities": ["Intent routing", "Multi-agent coordination", "Answer synthesis"],
    },
    {
        "id": "harvest",
        "name": "Harvest Agent",
        "type": "Decision intelligence",
        "status": "active",
        "description": "Combines crop knowledge and weather observations for harvest readiness decisions.",
        "capabilities": ["Crop knowledge", "Weather checks", "Harvest recommendations"],
    },
    {
        "id": "climate",
        "name": "Climate Agent",
        "type": "Environmental intelligence",
        "status": "active",
        "description": "Retrieves current conditions and multi-day Open-Meteo forecasts.",
        "capabilities": ["Current weather", "Forecasts", "Rain and wind risk"],
    },
    {
        "id": "market",
        "name": "Market Agent",
        "type": "Market intelligence",
        "status": "active",
        "description": "Fetches regional OGD/AGMARKNET mandi observations, compares nearby mandis, maintains price history and produces validated short-term forecasts.",
        "capabilities": ["Regional live/daily mandi prices", "Nearby mandi discovery", "Walk-forward price forecasting", "Market watch and price tape", "Market risk and net-return context"],
    },
    {
        "id": "logistics",
        "name": "Logistics Agent",
        "type": "Supply-chain optimization",
        "status": "active",
        "description": "Plans produce movement using geocoding, road routing, weather, vehicle selection and cost estimates.",
        "capabilities": ["Route planning", "Vehicle selection", "Transport cost and risk"],
    },
    {
        "id": "disease",
        "name": "Disease Agent",
        "type": "Planned module",
        "status": "planned",
        "description": "A package placeholder exists, but a working disease-diagnosis workflow is not present in this source bundle.",
        "capabilities": [],
    },
    {
        "id": "storage",
        "name": "Storage Agent",
        "type": "Planned module",
        "status": "planned",
        "description": "Storage knowledge and decision utilities exist in parts of the repository, but no complete standalone storage agent is wired into the coordinator.",
        "capabilities": [],
    },
]

app = FastAPI(
    title="AgriTwin Multi-Agent System",
    description="Web interface and API for the AgriTwin agricultural supply-chain multi-agent runtime.",
    version="1.0.0",
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    market = _market_snapshot()
    provider_configured = bool(os.getenv("GROQ_API_KEY") or GROQ_API_KEY)
    return {
        "status": "ready" if provider_configured else "setup_required",
        "provider": "Groq (OpenAI-compatible API)",
        "provider_configured": provider_configured,
        "active_agents": 4,
        "market_data": market,
        "market_live_api_configured": bool(os.getenv("DATA_GOV_API_KEY")),
        "market_live_source": "OGD / AGMARKNET daily price resource",
        "market_refresh_interval_seconds": 300,
    }


@app.get("/api/market/watch")
def market_watch(
    region: str = "Nashik",
    commodity: str = "Onion",
    horizon: int = 7,
) -> dict[str, Any]:
    """Regional market watch: observed mandi quotes plus a labelled forecast."""
    try:
        return _safe_json(
            MARKET_RUNTIME.get_market_dashboard(
                region=region,
                commodity=commodity,
                horizon=horizon,
                force_refresh=False,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Market watch request failed")
        raise HTTPException(
            status_code=502,
            detail="The Market Agent could not retrieve market data. Check the server log and API configuration.",
        ) from exc


@app.post("/api/market/watch/refresh")
def refresh_market_watch(payload: dict[str, Any]) -> dict[str, Any]:
    """Force a fresh source check for the market watch panel."""
    region = str(payload.get("region") or "Nashik").strip()
    commodity = str(payload.get("commodity") or "Onion").strip()
    try:
        horizon = int(payload.get("horizon") or 7)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Forecast horizon must be an integer.") from exc
    if not 1 <= horizon <= 30:
        raise HTTPException(status_code=422, detail="Forecast horizon must be between 1 and 30 days.")
    try:
        return _safe_json(
            MARKET_RUNTIME.get_market_dashboard(
                region=region,
                commodity=commodity,
                horizon=horizon,
                force_refresh=True,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Forced market refresh failed")
        raise HTTPException(
            status_code=502,
            detail="The Market Agent could not refresh the market feed. Check the server terminal for details.",
        ) from exc


@app.get("/api/agents")
def list_agents() -> dict[str, Any]:
    return {"agents": AGENTS}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Please enter a message.")

    session_id = (request.session_id or str(uuid.uuid4())).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", session_id):
        raise HTTPException(status_code=422, detail="Invalid session identifier.")

    if not (os.getenv("GROQ_API_KEY") or GROQ_API_KEY):
        raise HTTPException(
            status_code=503,
            detail="AgriTwin is installed, but no Groq API key is configured. Add GROQ_API_KEY to the .env file, then restart the server.",
        )

    try:
        runtime = session_manager.get(session_id)
        result, agents_used, observations = runtime.run(request.agent, message)
    except RuntimeError as exc:
        LOGGER.exception("LLM/runtime failure")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Unexpected AgriTwin request failure")
        raise HTTPException(
            status_code=500,
            detail="AgriTwin could not complete this request. Check the server terminal for the diagnostic details.",
        ) from exc

    labels = {
        "coordinator": "AgriTwin Coordinator",
        "harvest": "Harvest Agent",
        "climate": "Climate Agent",
        "market": "Market Agent",
        "logistics": "Logistics Agent",
    }
    return ChatResponse(
        session_id=session_id,
        agent=request.agent,
        agent_label=labels[request.agent],
        agents_used=agents_used,
        response=_safe_json(result),
        observations=_safe_json(observations),
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
