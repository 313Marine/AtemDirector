"""Unit tests for ATEM manager."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from atem_director.atem_layer.manager import ATEMManager
from atem_director.atem_layer.models import ConnectionState
from atem_director.config import ATEMConfig


@pytest.fixture
def atem_config() -> ATEMConfig:
    """Create ATEM config for testing."""
    return ATEMConfig(
        host="127.0.0.1",
        port=21124,
        connection_timeout=1.0,
        reconnect_attempts=2,
        reconnect_delay=0.1,
    )


@pytest.mark.asyncio
async def test_atem_manager_initialization(atem_config: ATEMConfig) -> None:
    """Test ATEM manager initialization."""
    manager = ATEMManager(atem_config)
    
    assert manager.config == atem_config
    assert manager.is_connected is False
    assert manager._state.state == ConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_is_connected_property(atem_config: ATEMConfig) -> None:
    """Test is_connected property."""
    manager = ATEMManager(atem_config)
    
    assert manager.is_connected is False
    
    manager._is_connected = True
    assert manager.is_connected is True


@pytest.mark.asyncio
async def test_get_status_disconnected(atem_config: ATEMConfig) -> None:
    """Test getting status when disconnected."""
    manager = ATEMManager(atem_config)
    
    status = await manager.get_status()
    
    assert status.state == ConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_get_switcher_state(atem_config: ATEMConfig) -> None:
    """Test getting switcher state."""
    manager = ATEMManager(atem_config)
    manager._is_connected = True
    
    state = await manager.get_switcher_state()
    
    assert state.program_input == 0
    assert state.preview_input == 1


@pytest.mark.asyncio
async def test_set_program_input_not_connected(atem_config: ATEMConfig) -> None:
    """Test setting program input when not connected."""
    manager = ATEMManager(atem_config)
    
    with pytest.raises(RuntimeError, match="not connected"):
        await manager.set_program_input(1)


@pytest.mark.asyncio
async def test_disconnect(atem_config: ATEMConfig) -> None:
    """Test disconnecting from ATEM device."""
    manager = ATEMManager(atem_config)
    manager._is_connected = True
    manager.connection = MagicMock()
    
    await manager.disconnect()
    
    assert manager.is_connected is False
    assert manager._state.state == ConnectionState.DISCONNECTED
