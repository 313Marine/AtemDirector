"""Integration tests for orchestrator."""
import pytest

from atem_director.engine.preset import PresetConfig
from atem_director.services.orchestrator import SwitchingOrchestrator


@pytest.mark.asyncio
async def test_execute_preset_not_connected(
    switching_orchestrator: SwitchingOrchestrator,
) -> None:
    """Test executing preset when ATEM not connected."""
    preset_config = PresetConfig(program_input=1, preview_input=2)
    switching_orchestrator.preset_manager.create_preset("test", preset_config)
    
    with pytest.raises(RuntimeError, match="not connected"):
        await switching_orchestrator.execute_preset("test")


@pytest.mark.asyncio
async def test_execute_nonexistent_preset(
    switching_orchestrator: SwitchingOrchestrator,
) -> None:
    """Test executing non-existent preset."""
    with pytest.raises(ValueError, match="not found"):
        await switching_orchestrator.execute_preset("nonexistent")


@pytest.mark.asyncio
async def test_quick_switch_not_connected(
    switching_orchestrator: SwitchingOrchestrator,
) -> None:
    """Test quick switch when ATEM not connected."""
    with pytest.raises(RuntimeError, match="not connected"):
        await switching_orchestrator.quick_switch(1)
