"""Health check endpoints."""
from fastapi import APIRouter, Request

from atem_director.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint."""
    # atem_manager is owned by the orchestrator
    orchestrator = getattr(request.app.state, 'orchestrator', None)
    atem_connected = (
        orchestrator.atem_manager.is_connected
        if orchestrator and hasattr(orchestrator, 'atem_manager')
        else False
    )
    return {
        "status": "ok",
        "atem_connected": atem_connected,
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    return {
        "ready": True,
    }
