"""Switcher control endpoints."""
from fastapi import APIRouter, Request, HTTPException, status

from atem_director.api.schemas import (
    PresetRequest,
    PresetResponse,
    SwitcherStateResponse,
    ATEMStatusResponse,
)
from atem_director.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/status", response_model=ATEMStatusResponse)
async def get_status(request: Request) -> ATEMStatusResponse:
    """Get ATEM device status.
    
    Returns:
        ATEM status response
    """
    atem_manager = request.app.state.atem_manager
    status = await atem_manager.get_status()
    
    return ATEMStatusResponse(
        model=status.model.value if status.model else None,
        state=status.state.value,
        firmware_version=status.firmware_version,
        uptime_seconds=status.uptime_seconds,
        is_connected=atem_manager.is_connected,
    )


@router.get("/state", response_model=SwitcherStateResponse)
async def get_state(request: Request) -> SwitcherStateResponse:
    """Get current switcher state.
    
    Returns:
        Switcher state response
    """
    atem_manager = request.app.state.atem_manager
    
    if not atem_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ATEM device not connected",
        )
    
    switcher_state = await atem_manager.get_switcher_state()
    
    return SwitcherStateResponse(
        program_input=switcher_state.program_input,
        preview_input=switcher_state.preview_input,
        transition_position=switcher_state.transition_position,
        transition_duration=switcher_state.transition_duration,
        is_transitioning=switcher_state.is_transitioning,
    )


@router.post("/program/{input_index}")
async def set_program(request: Request, input_index: int) -> dict:
    """Set program input.
    
    Args:
        input_index: Input index to set
        
    Returns:
        Response status
    """
    atem_manager = request.app.state.atem_manager
    
    if not atem_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ATEM device not connected",
        )
    
    await atem_manager.set_program_input(input_index)
    
    logger.info("Program input set", input_index=input_index)
    
    return {"status": "ok", "program_input": input_index}


@router.post("/preview/{input_index}")
async def set_preview(request: Request, input_index: int) -> dict:
    """Set preview input.
    
    Args:
        input_index: Input index to set
        
    Returns:
        Response status
    """
    atem_manager = request.app.state.atem_manager
    
    if not atem_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ATEM device not connected",
        )
    
    await atem_manager.set_preview_input(input_index)
    
    logger.info("Preview input set", input_index=input_index)
    
    return {"status": "ok", "preview_input": input_index}


@router.post("/presets", response_model=PresetResponse)
async def create_preset(preset_req: PresetRequest) -> PresetResponse:
    """Create a new switching preset.
    
    Args:
        preset_req: Preset creation request
        
    Returns:
        Created preset response
    """
    logger.info("Creating preset", name=preset_req.name)
    
    # In production, this would store in database via repository
    
    return PresetResponse(
        name=preset_req.name,
        description=preset_req.description,
        program_input=preset_req.program_input,
        preview_input=preset_req.preview_input,
        transition_duration=preset_req.transition_duration,
    )


@router.get("/presets/{preset_name}", response_model=PresetResponse)
async def get_preset(preset_name: str) -> PresetResponse:
    """Get a preset by name.
    
    Args:
        preset_name: Preset name
        
    Returns:
        Preset response
    """
    # In production, this would fetch from database via repository
    
    return PresetResponse(
        name=preset_name,
        description="Sample preset",
        program_input=1,
        preview_input=2,
        transition_duration=30,
    )


@router.post("/presets/{preset_name}/execute")
async def execute_preset(request: Request, preset_name: str) -> dict:
    """Execute a switching preset.
    
    Args:
        preset_name: Preset name to execute
        
    Returns:
        Execution status
    """
    atem_manager = request.app.state.atem_manager
    
    if not atem_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ATEM device not connected",
        )
    
    logger.info("Executing preset", preset_name=preset_name)
    
    # In production, this would use SwitchingOrchestrator
    
    return {"status": "ok", "preset": preset_name}
