from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text

from backend.app.api.auth import router as auth_router
from backend.app.api.users import router as users_router
from backend.app.api.agents import router as agents_router
from backend.app.api.marketplace import router as marketplace_router, connections_router
from backend.app.api.role_workspace import router as role_workspace_router
from backend.app.api.ai_chat import router as ai_chat_router
from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.core.redis import redis_client
from backend.app.exceptions.handlers import register_exception_handlers

app = FastAPI(
    title=settings.app_name,
    description="Backend API for the AgriTwin agricultural supply chain platform.",
    version="0.1.0",
    debug=settings.debug,
)

# Register global exception handlers
register_exception_handlers(app)

# Register all API routers here
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(agents_router)
app.include_router(marketplace_router)
app.include_router(connections_router)
app.include_router(role_workspace_router)
app.include_router(ai_chat_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/app/")


@app.get("/api", include_in_schema=False)
async def api_root():
    return {"message": "AgriTwin API is running", "environment": settings.app_env, "docs": "/docs", "frontend": "/app/"}


@app.get("/health")
async def health_check():
    database_status = "unhealthy"
    redis_status = "unhealthy"

    # Check PostgreSQL
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception:
        database_status = "unhealthy"

    # Check Redis
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    overall_status = (
        "healthy"
        if database_status == "healthy"
        and redis_status == "healthy"
        else "degraded"
    )

    return {
        "status": overall_status,
        "service": settings.app_name,
        "dependencies": {
            "postgresql": database_status,
            "redis": redis_status,
        },
    }

# Serve the AgriTwin dashboard from the same origin as the API.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
