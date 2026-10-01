from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.content import router as content_router
from app.api.routes.fixtures import router as fixtures_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.teams import router as teams_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["system"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(teams_router, tags=["teams"])
api_router.include_router(fixtures_router, tags=["fixtures"])
api_router.include_router(content_router, tags=["content"])
api_router.include_router(jobs_router, tags=["jobs"])
