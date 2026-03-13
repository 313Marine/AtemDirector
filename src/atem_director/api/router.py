"""API routers initialization."""
from fastapi import APIRouter

from atem_director.api import health, auth, switcher

router = APIRouter()

# Include routers
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(switcher.router, prefix="/switcher", tags=["switcher"])

__all__ = ["router"]
