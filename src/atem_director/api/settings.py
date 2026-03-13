"""Settings and configuration endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime

from atem_director.logging import get_logger
from atem_director.api.schemas import (
    OperationResponse,
    ChangeATEMIPRequest,
    ChangeTransitionModeRequest,
    ChangeMixDurationRequest,
    ChangeInputEnabledRequest,
    SetSafeCameraRequest,
    SetSwitchModeRequest,
    SetCameraWeightRequest,
    AdjustCooldownRequest,
    AddIntervalRequest,
    RemoveIntervalRequest,
    EnableIntervalRequest,
    DisableIntervalRequest,
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


@router.post("/atem/ip", response_model=OperationResponse)
async def change_atem_ip(
    request: ChangeATEMIPRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Change ATEM device IP and port."""
    try:
        await orchestrator.change_atem_ip(host=request.host, port=request.port)
        return OperationResponse(
            success=True,
            message=f"ATEM IP changed to {request.host}:{request.port}",
            operation="change_atem_ip",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to change ATEM IP", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition/mode", response_model=OperationResponse)
async def change_transition_mode(
    request: ChangeTransitionModeRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Change transition mode (cut or mix)."""
    try:
        await orchestrator.change_transition_mode(mode=request.mode)
        return OperationResponse(
            success=True,
            message=f"Transition mode changed to {request.mode}",
            operation="change_transition_mode",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to change transition mode", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition/duration", response_model=OperationResponse)
async def change_mix_duration(
    request: ChangeMixDurationRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Change mix transition duration."""
    try:
        await orchestrator.change_mix_duration(duration_ms=request.duration_ms)
        return OperationResponse(
            success=True,
            message=f"Mix duration changed to {request.duration_ms}ms",
            operation="change_mix_duration",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to change mix duration", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/input/enable", response_model=OperationResponse)
async def enable_input(
    request: ChangeInputEnabledRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Enable or disable input for auto switching."""
    try:
        await orchestrator.set_input_enabled(
            input_index=request.input_index,
            enabled=request.enabled,
        )
        action = "enabled" if request.enabled else "disabled"
        return OperationResponse(
            success=True,
            message=f"Input {request.input_index} {action}",
            operation="set_input_enabled",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to change input enabled state", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/safe-camera", response_model=OperationResponse)
async def set_safe_camera(
    request: SetSafeCameraRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Set safe camera fallback."""
    try:
        await orchestrator.set_safe_camera(input_index=request.input_index)
        return OperationResponse(
            success=True,
            message=f"Safe camera set to input {request.input_index}",
            operation="set_safe_camera",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to set safe camera", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-mode", response_model=OperationResponse)
async def set_switch_mode(
    request: SetSwitchModeRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Set switching mode (pure_random, balanced_random, weighted_random, round_robin_random)."""
    try:
        await orchestrator.set_switch_mode(mode=request.mode)
        return OperationResponse(
            success=True,
            message=f"Switch mode changed to {request.mode}",
            operation="set_switch_mode",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to set switch mode", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/camera-weight", response_model=OperationResponse)
async def set_camera_weight(
    request: SetCameraWeightRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Set per-camera weight for weighted random mode."""
    try:
        await orchestrator.set_camera_weight(
            input_index=request.input_index,
            weight=request.weight,
        )
        return OperationResponse(
            success=True,
            message=f"Weight for input {request.input_index} set to {request.weight}",
            operation="set_camera_weight",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to set camera weight", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cooldown", response_model=OperationResponse)
async def adjust_cooldown(
    request: AdjustCooldownRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Adjust cooldown settings."""
    try:
        await orchestrator.adjust_cooldown(
            cooldown_seconds=request.cooldown_seconds,
        )
        return OperationResponse(
            success=True,
            message=f"Cooldown set to {request.cooldown_seconds} seconds",
            operation="adjust_cooldown",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to adjust cooldown", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intervals/add", response_model=OperationResponse)
async def add_interval(
    request: AddIntervalRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Add custom interval to pool."""
    try:
        await orchestrator.add_interval(
            interval_seconds=request.interval_seconds,
            name=request.name,
        )
        return OperationResponse(
            success=True,
            message=f"Added interval {request.interval_seconds}s",
            operation="add_interval",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to add interval", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intervals/remove", response_model=OperationResponse)
async def remove_interval(
    request: RemoveIntervalRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Remove interval from pool."""
    try:
        await orchestrator.remove_interval(interval_seconds=request.interval_seconds)
        return OperationResponse(
            success=True,
            message=f"Removed interval {request.interval_seconds}s",
            operation="remove_interval",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to remove interval", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intervals/enable", response_model=OperationResponse)
async def enable_interval(
    request: EnableIntervalRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Enable interval in active pool."""
    try:
        await orchestrator.enable_interval(interval_seconds=request.interval_seconds)
        return OperationResponse(
            success=True,
            message=f"Enabled interval {request.interval_seconds}s",
            operation="enable_interval",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to enable interval", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intervals/disable", response_model=OperationResponse)
async def disable_interval(
    request: DisableIntervalRequest,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
) -> OperationResponse:
    """Disable interval in active pool."""
    try:
        await orchestrator.disable_interval(interval_seconds=request.interval_seconds)
        return OperationResponse(
            success=True,
            message=f"Disabled interval {request.interval_seconds}s",
            operation="disable_interval",
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to disable interval", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
