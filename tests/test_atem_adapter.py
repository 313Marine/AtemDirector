"""Tests for ATEM adapter layer."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from atem_director.atem_layer.manager import (
    ATEMManager,
    PyATEMAdapter,
    ATEMProtocolAdapter,
    TransitionMode,
)
from atem_director.atem_layer.models import (
    ConnectionState,
    InputSignalState,
    ATEMCapabilities,
)
from atem_director.config import ATEMConfig


class MockATEMAdapter(ATEMProtocolAdapter):
    """Mock ATEM adapter for testing."""
    
    def __init__(self) -> None:
        """Initialize mock adapter."""
        self.connected = False
        self.program_input = 1
        self.preview_input = 2
        self.transition_mode = TransitionMode.CUT
        self.mix_duration_ms = 300
        self.input_signals = {i: i <= 4 for i in range(1, 9)}
        self.streaming_active = False
        self.recording_active = False
        self.call_count = {}
    
    async def connect(self, host: str, port: int, timeout: float = 5.0) -> None:
        """Mock connect."""
        self._track_call("connect")
        if host == "invalid":
            raise ConnectionError("Invalid host")
        await asyncio.sleep(0.01)
        self.connected = True
    
    async def disconnect(self) -> None:
        """Mock disconnect."""
        self._track_call("disconnect")
        self.connected = False
    
    async def get_device_info(self) -> dict:
        """Mock get device info."""
        self._track_call("get_device_info")
        return {
            "model": "ATEM Mini Extreme ISO 12G",
            "firmware": "1.0.0",
            "inputs": 4,
            "outputs": 2,
        }
    
    async def get_input_signals(self) -> dict:
        """Mock get input signals."""
        self._track_call("get_input_signals")
        return self.input_signals.copy()
    
    async def get_program_input(self) -> int:
        """Mock get program input."""
        self._track_call("get_program_input")
        return self.program_input
    
    async def get_preview_input(self) -> int:
        """Mock get preview input."""
        self._track_call("get_preview_input")
        return self.preview_input
    
    async def set_program_input(self, input_index: int) -> None:
        """Mock set program input."""
        self._track_call("set_program_input")
        self.program_input = input_index
    
    async def set_preview_input(self, input_index: int) -> None:
        """Mock set preview input."""
        self._track_call("set_preview_input")
        self.preview_input = input_index
    
    async def set_transition_mode(self, mode: TransitionMode) -> None:
        """Mock set transition mode."""
        self._track_call("set_transition_mode")
        self.transition_mode = mode
    
    async def set_mix_duration(self, duration_ms: int) -> None:
        """Mock set mix duration."""
        self._track_call("set_mix_duration")
        self.mix_duration_ms = duration_ms
    
    async def perform_cut(self) -> None:
        """Mock perform cut."""
        self._track_call("perform_cut")
    
    async def get_streaming_status(self) -> bool:
        """Mock get streaming status."""
        self._track_call("get_streaming_status")
        return self.streaming_active
    
    async def get_recording_status(self) -> bool:
        """Mock get recording status."""
        self._track_call("get_recording_status")
        return self.recording_active
    
    def _track_call(self, method: str) -> None:
        """Track method calls for testing."""
        self.call_count[method] = self.call_count.get(method, 0) + 1


@pytest.fixture
def atem_config() -> ATEMConfig:
    """Create test ATEM config."""
    return ATEMConfig(
        host="192.168.1.100",
        port=21124,
        reconnect_attempts=3,
        reconnect_delay=0.1,
        connection_timeout=2.0,
    )


@pytest.fixture
def mock_adapter() -> MockATEMAdapter:
    """Create mock adapter."""
    return MockATEMAdapter()


@pytest.fixture
def atem_manager(atem_config: ATEMConfig, mock_adapter: MockATEMAdapter) -> ATEMManager:
    """Create ATEM manager with mock adapter."""
    return ATEMManager(atem_config, adapter=mock_adapter)


class TestATEMConnectionStates:
    """Test connection state management."""
    
    async def test_initial_state_disconnected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test initial connection state is disconnected."""
        assert atem_manager.connection_state == ConnectionState.DISCONNECTED
        assert not atem_manager.is_connected
    
    async def test_connect_success(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test successful connection."""
        await atem_manager.connect()
        
        assert atem_manager.connection_state == ConnectionState.CONNECTED
        assert atem_manager.is_connected
    
    async def test_disconnect(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test disconnect."""
        await atem_manager.connect()
        assert atem_manager.is_connected
        
        await atem_manager.disconnect()
        assert atem_manager.connection_state == ConnectionState.DISCONNECTED
        assert not atem_manager.is_connected
    
    async def test_connection_error_state(
        self,
        atem_config: ATEMConfig,
        mock_adapter: MockATEMAdapter,
    ) -> None:
        """Test error state on failed connection."""
        # Setup adapter to fail
        mock_adapter.connected = False
        
        async def failing_connect(host: str, port: int, timeout: float = 5.0) -> None:
            raise ConnectionError("Mock failure")
        
        mock_adapter.connect = failing_connect
        
        manager = ATEMManager(atem_config, adapter=mock_adapter)
        await manager.connect()
        
        assert manager.connection_state == ConnectionState.ERROR
        assert not manager.is_connected


class TestConnectionCallbacks:
    """Test connection state callbacks."""
    
    async def test_connection_callback(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test connection state callback."""
        states_received = []
        
        def callback(state: ConnectionState) -> None:
            states_received.append(state)
        
        atem_manager.register_connection_callback(callback)
        await atem_manager.connect()
        
        assert ConnectionState.CONNECTED in states_received
    
    async def test_disconnect_callback(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test disconnect callback."""
        states_received = []
        
        def callback(state: ConnectionState) -> None:
            states_received.append(state)
        
        atem_manager.register_connection_callback(callback)
        await atem_manager.connect()
        await atem_manager.disconnect()
        
        assert ConnectionState.DISCONNECTED in states_received


class TestSwitcherControl:
    """Test switcher control operations."""
    
    async def test_set_program_input_connected(
        self,
        atem_manager: ATEMManager,
        mock_adapter: MockATEMAdapter,
    ) -> None:
        """Test setting program input when connected."""
        await atem_manager.connect()
        
        await atem_manager.set_program_input(3)
        
        state = await atem_manager.get_switcher_state()
        assert state.program_input == 3
    
    async def test_set_program_input_disconnected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test setting program input when disconnected."""
        with pytest.raises(RuntimeError):
            await atem_manager.set_program_input(3)
    
    async def test_set_preview_input_connected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test setting preview input when connected."""
        await atem_manager.connect()
        
        await atem_manager.set_preview_input(4)
        
        state = await atem_manager.get_switcher_state()
        assert state.preview_input == 4
    
    async def test_set_preview_input_disconnected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test setting preview input when disconnected."""
        with pytest.raises(RuntimeError):
            await atem_manager.set_preview_input(4)
    
    async def test_set_transition_mode(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test setting transition mode."""
        await atem_manager.connect()
        
        await atem_manager.set_transition_mode(TransitionMode.MIX)
        
        state = await atem_manager.get_switcher_state()
        assert state.transition_mode == TransitionMode.MIX
    
    async def test_set_mix_duration(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test setting mix duration."""
        await atem_manager.connect()
        
        await atem_manager.set_mix_duration(500)
        
        state = await atem_manager.get_switcher_state()
        assert state.transition_duration_ms == 500
    
    async def test_panic_cut_connected(
        self,
        atem_manager: ATEMManager,
        mock_adapter: MockATEMAdapter,
    ) -> None:
        """Test panic cut when connected."""
        await atem_manager.connect()
        
        await atem_manager.panic_cut()
        
        assert mock_adapter.call_count.get("perform_cut", 0) > 0
    
    async def test_panic_cut_disconnected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test panic cut doesn't raise when disconnected."""
        # Panic cut should be best-effort and not raise
        await atem_manager.panic_cut()


class TestInputMonitoring:
    """Test input signal monitoring."""
    
    async def test_input_signals_monitoring(
        self,
        atem_manager: ATEMManager,
        mock_adapter: MockATEMAdapter,
    ) -> None:
        """Test input signals are monitored."""
        await atem_manager.connect()
        
        # Wait for monitoring to update
        await asyncio.sleep(0.2)
        
        state = await atem_manager.get_switcher_state()
        
        # Should have input signals for inputs 1-8
        assert len(state.input_signals) > 0
        
        # Check signal states
        for input_idx, signal in state.input_signals.items():
            assert signal.input_index == input_idx
            assert signal.signal_state in [
                InputSignalState.NONE,
                InputSignalState.PROGRAM,
                InputSignalState.PREVIEW,
            ]


class TestDeviceStatus:
    """Test device status retrieval."""
    
    async def test_get_status_disconnected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test get status when disconnected."""
        status = await atem_manager.get_status()
        
        assert status.state == ConnectionState.DISCONNECTED
    
    async def test_get_status_connected(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test get status when connected."""
        await atem_manager.connect()
        
        status = await atem_manager.get_status()
        
        assert status.state == ConnectionState.CONNECTED
        assert status.model is not None
        assert status.firmware_version is not None
    
    async def test_connection_metrics(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test connection metrics tracking."""
        await atem_manager.connect()
        
        metrics = atem_manager.metrics
        
        assert metrics.total_attempts > 0
        assert metrics.successful_connections > 0
        assert metrics.last_successful_time is not None


class TestCapabilityHandling:
    """Test capability-based behavior."""
    
    async def test_mix_transition_fallback_to_cut(
        self,
        atem_config: ATEMConfig,
        mock_adapter: MockATEMAdapter,
    ) -> None:
        """Test falls back to cut if mix transition not supported."""
        manager = ATEMManager(atem_config, adapter=mock_adapter)
        
        # Disable mix transition support
        manager._status.capabilities.supports_mix_transition = False
        
        await manager.connect()
        
        # Requesting mix should use cut instead
        await manager.set_transition_mode(TransitionMode.MIX)
        
        state = await manager.get_switcher_state()
        # Should have logged warning and used cut as fallback
        assert mock_adapter.transition_mode == TransitionMode.CUT or state.transition_mode == TransitionMode.CUT


class TestErrorHandling:
    """Test error handling and fallback behaviors."""
    
    async def test_invalid_input_range(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test error on invalid input range."""
        await atem_manager.connect()
        
        with pytest.raises(ValueError):
            await atem_manager.set_program_input(999)
    
    async def test_invalid_mix_duration(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test error on invalid mix duration."""
        await atem_manager.connect()
        
        with pytest.raises(ValueError):
            await atem_manager.set_mix_duration(999999)
    
    async def test_reconnect(
        self,
        atem_manager: ATEMManager,
    ) -> None:
        """Test reconnect functionality."""
        await atem_manager.connect()
        assert atem_manager.is_connected
        
        await atem_manager.reconnect()
        
        # Should be reconnected
        assert atem_manager.is_connected
