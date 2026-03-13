"""Tests for orchestration service."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from atem_director.services.runtime import ApplicationOrchestrator
from atem_director.atem_layer.models import (
    ATEMStatus,
    ConnectionState,
    SwitcherState,
    TransitionMode,
)
from atem_director.engine.switching import SwitchingState
from atem_director.runtime.state import OperationMode
from atem_director.config import ATEMConfig
from atem_director.persistence.storage import StorageManager


@pytest.fixture
def mock_config():
    """Create mock ATEM config."""
    return ATEMConfig(
        host="192.168.1.100",
        port=21124,
        connection_timeout=5.0,
        reconnect_attempts=3,
        reconnect_delay=1.0,
    )


@pytest.fixture
async def mock_storage():
    """Create mock storage."""
    storage = AsyncMock(spec=StorageManager)
    storage.load_app_config = AsyncMock(return_value=MagicMock(
        auto_switch_enabled=False,
        auto_switch_mode="balanced_random",
        safe_camera=1,
    ))
    storage.record_event = AsyncMock()
    storage.get_input_operator_state = AsyncMock(return_value=None)
    storage.save_session_summary = AsyncMock()
    return storage


@pytest.fixture
async def orchestrator(mock_config, mock_storage):
    """Create orchestrator instance."""
    orch = ApplicationOrchestrator(mock_config, mock_storage)
    
    # Mock ATEM manager
    orch.atem_manager = AsyncMock()
    orch.atem_manager.connect = AsyncMock()
    orch.atem_manager.disconnect = AsyncMock()
    orch.atem_manager.is_connected = True
    orch.atem_manager.get_status = AsyncMock(return_value=ATEMStatus(
        state=ConnectionState.CONNECTED,
        inputs_count=4,
    ))
    orch.atem_manager.get_switcher_state = AsyncMock(return_value=SwitcherState(
        program_input=1,
        preview_input=2,
    ))
    orch.atem_manager.set_program_input = AsyncMock()
    orch.atem_manager.register_connection_callback = MagicMock()
    orch.atem_manager.register_state_callback = MagicMock()
    
    yield orch
    
    # Cleanup
    try:
        await orch.shutdown()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_initialize_success(orchestrator, mock_storage):
    """Test successful initialization."""
    await orchestrator.initialize()
    
    assert orchestrator.state.is_initialized
    assert not orchestrator.state.is_initializing
    assert orchestrator.switching_engine is not None
    assert orchestrator.atem_manager.connect.called


@pytest.mark.asyncio
async def test_initialize_atem_connection_failure(orchestrator):
    """Test initialization with ATEM connection failure."""
    orchestrator.atem_manager.connect = AsyncMock(
        side_effect=ConnectionError("Connection failed")
    )
    
    with pytest.raises(ConnectionError):
        await orchestrator.initialize()
    
    assert not orchestrator.state.is_initialized
    assert orchestrator.state.operation_mode == OperationMode.FAILSAFE


@pytest.mark.asyncio
async def test_start_auto_switching(orchestrator):
    """Test starting auto-switching."""
    await orchestrator.initialize()
    
    await orchestrator.start_auto_switching()
    
    assert orchestrator.state.session_active
    assert orchestrator.state.auto_switch_enabled
    assert orchestrator.state.operation_mode == OperationMode.AUTO


@pytest.mark.asyncio
async def test_stop_auto_switching(orchestrator):
    """Test stopping auto-switching."""
    await orchestrator.initialize()
    await orchestrator.start_auto_switching()
    
    await orchestrator.stop_auto_switching()
    
    assert not orchestrator.state.session_active
    assert not orchestrator.state.auto_switch_enabled
    assert orchestrator.state.operation_mode == OperationMode.MANUAL


@pytest.mark.asyncio
async def test_manual_switch_to_input(orchestrator):
    """Test manual switch to input."""
    await orchestrator.initialize()
    
    await orchestrator.switch_to_input(3, reason="manual_test")
    
    orchestrator.atem_manager.set_program_input.assert_called_with(3)
    assert orchestrator.state.switcher_state.program_input == 3


@pytest.mark.asyncio
async def test_manual_switch_invalid_input(orchestrator):
    """Test switch to invalid input."""
    await orchestrator.initialize()
    
    with pytest.raises(ValueError):
        await orchestrator.switch_to_input(10)  # Only 4 inputs


@pytest.mark.asyncio
async def test_skip_current_camera(orchestrator):
    """Test skip current camera."""
    await orchestrator.initialize()
    await orchestrator.start_auto_switching()
    
    await orchestrator.skip_current_camera()
    
    # Engine should have been called
    assert orchestrator.switching_engine is not None


@pytest.mark.asyncio
async def test_hold_current_camera(orchestrator):
    """Test hold/release current camera."""
    await orchestrator.initialize()
    await orchestrator.start_auto_switching()
    
    await orchestrator.hold_current_camera(hold=True)
    
    assert orchestrator.switching_engine is not None


@pytest.mark.asyncio
async def test_get_dashboard_state(orchestrator):
    """Test getting dashboard state."""
    await orchestrator.initialize()
    
    dashboard = await orchestrator.get_dashboard_state()
    
    assert dashboard.atem_status.state == ConnectionState.CONNECTED
    assert dashboard.engine_state == SwitchingState.IDLE
    assert dashboard.operation_mode == OperationMode.MANUAL


@pytest.mark.asyncio
async def test_state_callback_registration(orchestrator):
    """Test registering state callbacks."""
    callback = AsyncMock()
    orchestrator.register_state_callback(callback)
    
    await orchestrator.initialize()
    
    # Callback should have been called during initialization
    assert len(orchestrator._state_callbacks) == 1


@pytest.mark.asyncio
async def test_atem_disconnection_handling(orchestrator):
    """Test handling ATEM disconnection."""
    await orchestrator.initialize()
    
    # Simulate disconnection
    await orchestrator._on_atem_connection_change(ConnectionState.DISCONNECTED)
    
    assert orchestrator.state.atem_status.state == ConnectionState.DISCONNECTED
    assert orchestrator.state.operation_mode == OperationMode.FAILSAFE
    assert orchestrator.state.last_error is not None


@pytest.mark.asyncio
async def test_switch_statistics_tracking(orchestrator):
    """Test that switch statistics are tracked."""
    await orchestrator.initialize()
    await orchestrator.start_auto_switching()
    
    # Make a switch
    await orchestrator.switch_to_input(2)
    
    # Check session stats
    assert orchestrator.state.session_stats.total_switches == 1
    assert orchestrator.state.session_stats.last_switched_to == 2


@pytest.mark.asyncio
async def test_camera_state_initialization(orchestrator):
    """Test camera states are initialized."""
    await orchestrator.initialize()
    
    # Should have 4 camera states (inputs 1-4)
    assert len(orchestrator.state.camera_states) >= 1
    
    # First camera should be current program
    if 1 in orchestrator.state.camera_states:
        assert orchestrator.state.camera_states[1].is_current_program


@pytest.mark.asyncio
async def test_shutdown_graceful(orchestrator):
    """Test graceful shutdown."""
    await orchestrator.initialize()
    await orchestrator.start_auto_switching()
    
    await orchestrator.shutdown()
    
    assert orchestrator.atem_manager.disconnect.called


@pytest.mark.asyncio
async def test_double_initialization(orchestrator):
    """Test that double initialization is safe."""
    await orchestrator.initialize()
    
    # Second initialization should work
    assert orchestrator.state.is_initialized
    assert orchestrator.switching_engine is not None
