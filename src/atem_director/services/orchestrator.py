"""Orchestration service for switching operations."""
from typing import Optional

from atem_director.atem_layer.manager import ATEMManager
from atem_director.engine.preset import PresetManager, PresetConfig
from atem_director.logging import get_logger

logger = get_logger(__name__)


class SwitchingOrchestrator:
    """Orchestrates switching operations between ATEM manager and preset engine."""
    
    def __init__(self, atem_manager: ATEMManager, preset_manager: PresetManager) -> None:
        """Initialize switching orchestrator.
        
        Args:
            atem_manager: ATEM device manager
            preset_manager: Preset manager
        """
        self.atem_manager = atem_manager
        self.preset_manager = preset_manager
    
    async def execute_preset(self, preset_name: str) -> None:
        """Execute a switching preset.
        
        Args:
            preset_name: Name of preset to execute
        """
        preset = self.preset_manager.get_preset(preset_name)
        if preset is None:
            raise ValueError(f"Preset '{preset_name}' not found")
        
        if not self.atem_manager.is_connected:
            raise RuntimeError("ATEM device is not connected")
        
        logger.info("Executing preset", preset=preset_name)
        
        # Set preview input
        await self.atem_manager.set_preview_input(preset.preview_input)
        
        # Set program input
        await self.atem_manager.set_program_input(preset.program_input)
        
        # Activate in preset manager
        self.preset_manager.activate_preset(preset_name)
        
        logger.info(
            "Preset executed successfully",
            preset=preset_name,
            program_input=preset.program_input,
            preview_input=preset.preview_input,
        )
    
    async def quick_switch(self, input_index: int) -> None:
        """Quickly switch to input.
        
        Args:
            input_index: Input index to switch to
        """
        if not self.atem_manager.is_connected:
            raise RuntimeError("ATEM device is not connected")
        
        logger.info("Quick switching to input", input_index=input_index)
        await self.atem_manager.set_program_input(input_index)
