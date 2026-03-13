"""API routers initialization."""
from fastapi import APIRouter

from atem_director.api import health, auth, control, settings, data, websocket

router = APIRouter()

# Include routers
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(control.router, prefix="/control", tags=["control"])
router.include_router(settings.router, prefix="/settings", tags=["settings"])
router.include_router(data.router, prefix="/data", tags=["data"])
router.include_router(websocket.router, tags=["websocket"])

__all__ = ["router"]
