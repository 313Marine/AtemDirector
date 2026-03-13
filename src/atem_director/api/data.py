"""Data query endpoints for presets, statistics, and logs."""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from datetime import datetime
from typing import List

from atem_director.logging import get_logger
from atem_director.api.schemas import (
    PresetRequest,
    PresetResponse,
    LoadPresetRequest,
    OperationResponse,
    RuntimeStateResponse,
    SessionStatisticsResponse,
    LogQueryResponse,
)
from atem_director.services.runtime import ApplicationOrchestrator

logger = get_logger(__name__)

router = APIRouter()


async def get_orchestrator(request: Request) -> ApplicationOrchestrator:
    """Get orchestrator instance from app state."""
    orchestrator = getattr(request.app.state, 'orchestrator', None)
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Application not initialized")
    return orchestrator


# ============================================================================
# Preset Management Endpoints
# ============================================================================

@router.post("/presets/save", response_model=PresetResponse)
async def save_preset(
    preset: PresetRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> PresetResponse:
    """Save switching preset."""
    try:
        saved_preset = await orchestrator.save_preset(preset.dict())
        return PresetResponse(**saved_preset)
    except Exception as e:
        logger.error("Failed to save preset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets", response_model=List[PresetResponse])
async def list_presets(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> List[PresetResponse]:
    """List all saved presets."""
    try:
        presets = await orchestrator.list_presets()
        return [PresetResponse(**p) for p in presets]
    except Exception as e:
        logger.error("Failed to list presets", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: int,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> PresetResponse:
    """Get specific preset."""
    try:
        preset = await orchestrator.get_preset(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        return PresetResponse(**preset)
    except Exception as e:
        logger.error("Failed to get preset", error=str(e), preset_id=preset_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/presets/load", response_model=OperationResponse)
async def load_preset(
    request: LoadPresetRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Load preset configuration."""
    try:
        await orchestrator.load_preset(preset_id=request.preset_id)
        return OperationResponse(
            success=True,
            message=f"Preset {request.preset_id} loaded",
            operation="load_preset",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to load preset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/presets/{preset_id}", response_model=OperationResponse)
async def delete_preset(
    preset_id: int,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Delete preset."""
    try:
        await orchestrator.delete_preset(preset_id)
        return OperationResponse(
            success=True,
            message=f"Preset {preset_id} deleted",
            operation="delete_preset",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to delete preset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# State Query Endpoints
# ============================================================================

@router.get("/state", response_model=RuntimeStateResponse)
async def get_current_state(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> RuntimeStateResponse:
    """Get complete current application state."""
    try:
        state = await orchestrator.get_current_state()
        return RuntimeStateResponse(**state)
    except Exception as e:
        logger.error("Failed to get current state", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/statistics/session", response_model=SessionStatisticsResponse)
async def get_session_statistics(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> SessionStatisticsResponse:
    """Get current session statistics."""
    try:
        stats = await orchestrator.get_session_statistics()
        return SessionStatisticsResponse(**stats)
    except Exception as e:
        logger.error("Failed to get session statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/cumulative")
async def get_cumulative_statistics(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
):
    """Get cumulative all-time statistics."""
    try:
        stats = await orchestrator.get_cumulative_statistics()
        return stats
    except Exception as e:
        logger.error("Failed to get cumulative statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Log/Event Endpoints
# ============================================================================

@router.get("/logs", response_model=LogQueryResponse)
async def get_event_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    event_type: str = Query(None),
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> LogQueryResponse:
    """Get event logs with optional filtering."""
    try:
        logs = await orchestrator.get_event_logs(
            limit=limit,
            offset=offset,
            event_type=event_type,
        )
        return LogQueryResponse(**logs)
    except Exception as e:
        logger.error("Failed to get event logs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs/clear", response_model=OperationResponse)
async def clear_logs(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Clear all event logs."""
    try:
        await orchestrator.clear_logs()
        return OperationResponse(
            success=True,
            message="Event logs cleared",
            operation="clear_logs",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to clear logs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
