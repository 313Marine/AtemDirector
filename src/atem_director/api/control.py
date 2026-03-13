"""Control operation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime

from atem_director.logging import get_logger
from atem_director.api.schemas import (
    OperationResponse,
    ErrorResponse,
    SkipCurrentRequest,
    SkipNextRequest,
    ExtendCurrentRequest,
    HoldCurrentRequest,
    LockCurrentRequest,
    ReleaseLockRequest,
    PanicCutRequest,
    ReconnectATEMRequest,
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


@router.post("/start", response_model=OperationResponse)
async def start_auto_switching(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Start automatic switching."""
    try:
        await orchestrator.start_auto_switching()
        return OperationResponse(
            success=True,
            message="Auto switching started",
            operation="start",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to start auto switching", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=OperationResponse)
async def stop_auto_switching(
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Stop automatic switching."""
    try:
        await orchestrator.stop_auto_switching()
        return OperationResponse(
            success=True,
            message="Auto switching stopped",
            operation="stop",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to stop auto switching", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skip-current", response_model=OperationResponse)
async def skip_current_camera(
    request: SkipCurrentRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Skip current camera and switch immediately."""
    try:
        await orchestrator.skip_current(reason=request.reason)
        return OperationResponse(
            success=True,
            message="Skipped current camera",
            operation="skip_current",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to skip current camera", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skip-next", response_model=OperationResponse)
async def skip_next_switch(
    request: SkipNextRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Skip next scheduled switch."""
    try:
        await orchestrator.skip_next(reason=request.reason)
        return OperationResponse(
            success=True,
            message="Skipped next switch",
            operation="skip_next",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to skip next switch", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extend-current", response_model=OperationResponse)
async def extend_current_camera(
    request: ExtendCurrentRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Extend current camera hold time."""
    try:
        await orchestrator.extend_current(seconds=request.seconds)
        return OperationResponse(
            success=True,
            message=f"Extended current camera by {request.seconds} seconds",
            operation="extend_current",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to extend current camera", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hold-current", response_model=OperationResponse)
async def hold_current_camera(
    request: HoldCurrentRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Hold current camera indefinitely."""
    try:
        await orchestrator.hold_current(reason=request.reason)
        return OperationResponse(
            success=True,
            message="Held current camera",
            operation="hold_current",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to hold current camera", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lock-current", response_model=OperationResponse)
async def lock_current_camera(
    request: LockCurrentRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Lock current camera for specified duration."""
    try:
        await orchestrator.lock_current(
            seconds=request.seconds,
            reason=request.reason,
        )
        return OperationResponse(
            success=True,
            message=f"Locked current camera for {request.seconds} seconds",
            operation="lock_current",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to lock current camera", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/release-lock", response_model=OperationResponse)
async def release_camera_lock(
    request: ReleaseLockRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Release camera lock."""
    try:
        await orchestrator.release_lock(reason=request.reason)
        return OperationResponse(
            success=True,
            message="Released camera lock",
            operation="release_lock",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to release camera lock", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/panic-cut", response_model=OperationResponse)
async def panic_cut(
    request: PanicCutRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Perform immediate panic cut."""
    try:
        await orchestrator.panic_cut(reason=request.reason)
        return OperationResponse(
            success=True,
            message="Panic cut executed",
            operation="panic_cut",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to execute panic cut", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconnect-atem", response_model=OperationResponse)
async def reconnect_atem_device(
    request: ReconnectATEMRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Reconnect to ATEM device."""
    try:
        await orchestrator.reconnect_atem(reason=request.reason)
        return OperationResponse(
            success=True,
            message="Reconnecting to ATEM device",
            operation="reconnect_atem",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to reconnect to ATEM", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
