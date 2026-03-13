"""Health check endpoints."""
from fastapi import APIRouter, Request

from atem_director.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint."""
    atem_manager = request.app.state.atem_manager
    
    return {
        "status": "ok",
        "atem_connected": atem_manager.is_connected,
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    return {
        "ready": True,
    }
