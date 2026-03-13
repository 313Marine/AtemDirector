"""Orchestration service - application brain.

This service coordinates:
- ATEM adapter lifecycle and state
- Switching engine initialization and control
- Persistence layer (config, stats, events)
- Runtime state management
- WebSocket publication
- Error handling and recovery

Responsibilities:
- Boot application state
- Load persisted configuration
- Initialize ATEM adapter
- Initialize switching engine
- Sync ATEM state into runtime state
- Execute switch commands through adapter
- Record statistics on switches
- Record event logs
- Manage reconnect behavior
- React to signal changes, disconnects, manual changes
- Publish state updates

Design principles:
- Centralize orchestration here
- Keep routes thin, templates dumb
- Domain logic out of UI
- Safe edge case handling
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, List
from enum import Enum

from atem_director.logging import get_logger
from atem_director.atem_layer.manager import ATEMManager
from atem_director.atem_layer.models import (
    ATEMStatus,
    ConnectionState,
    SwitcherState,
    TransitionMode,
)
from atem_director.engine.switching import (
    SwitchingEngine,
    SwitchingState,
    SwitchingEvent,
    SwitchMode,
)
from atem_director.persistence.storage import StorageManager
from atem_director.runtime.state import (
    RuntimeState,
    CameraState,
    SwitchingSessionStats,
    OperationMode,
    DashboardState,
)
from atem_director.config import ATEMConfig

logger = get_logger(__name__)

# Type aliases
StateChangeCallback = Callable[[DashboardState], Any]


class ApplicationOrchestrator:
    """Application orchestrator - coordinates all subsystems."""
    
    def __init__(
        self,
        atem_config: ATEMConfig,
        storage: StorageManager,
    ) -> None:
        """Initialize orchestrator.
        
        Args:
            atem_config: ATEM device configuration
            storage: Persistence storage manager
        """
        self.atem_config = atem_config
        self.storage = storage
        
        # Subsystems
        self.atem_manager = ATEMManager(atem_config)
        self.switching_engine: Optional[SwitchingEngine] = None
        
        # Runtime state
        self.state = RuntimeState()
        self.state.atem_manager = self.atem_manager
        
        # Callbacks
        self._state_callbacks: List[StateChangeCallback] = []
        self._state_lock = asyncio.Lock()
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task[Any]] = None
        self._engine_tick_task: Optional[asyncio.Task[Any]] = None
        self._sync_stats_task: Optional[asyncio.Task[Any]] = None
    
    async def initialize(self) -> None:
        """Initialize application.
        
        Steps:
        1. Load persisted configuration
        2. Initialize ATEM connection
        3. Initialize switching engine
        4. Sync device state
        5. Start background monitoring
        """
        logger.info("Initializing ATEM Director application")
        
        async with self._state_lock:
            self.state.is_initializing = True
            self.state.total_initialization_attempts += 1
        
        try:
            # Load configuration
            logger.info("Loading persisted configuration")
            app_config = await self.storage.load_app_config()
            
            async with self._state_lock:
                self.state.auto_switch_enabled = app_config.auto_switch_enabled
                self.state.current_switch_mode = app_config.auto_switch_mode
                self.state.safe_camera = app_config.safe_camera
            
            # Connect to ATEM
            logger.info("Connecting to ATEM device")
            await self.atem_manager.connect()
            
            # Initialize switching engine
            logger.info("Initializing switching engine")
            self.switching_engine = SwitchingEngine(
                enabled_inputs=list(range(1, 9)),  # Inputs 1-8
                safe_camera=app_config.safe_camera,
                switch_mode=self._parse_switch_mode(app_config.auto_switch_mode),
            )
            
            async with self._state_lock:
                self.state.switching_engine = self.switching_engine
            
            # Register engine callbacks
            self.switching_engine.on_state_change(self._on_engine_state_change)
            self.switching_engine.on_switch(self._on_engine_switch)
            
            # Sync initial device state
            await self._sync_device_state()
            
            # Initialize camera states
            await self._initialize_camera_states(app_config)
            
            # Register ATEM callbacks
            self.atem_manager.register_connection_callback(
                self._on_atem_connection_change
            )
            self.atem_manager.register_state_callback(
                self._on_atem_state_change
            )
            
            # Start background tasks
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._sync_stats_task = asyncio.create_task(self._stats_sync_loop())
            
            async with self._state_lock:
                self.state.is_initialized = True
                self.state.is_initializing = False
                self.state.last_error = None
            
            logger.info("Application initialization complete")
            await self._publish_state_change()
            
        except Exception as e:
            logger.error("Application initialization failed", error=str(e))
            
            async with self._state_lock:
                self.state.is_initializing = False
                self.state.last_error = f"Initialization failed: {str(e)}"
                self.state.last_error_time = datetime.now()
                self.state.operation_mode = OperationMode.FAILSAFE
            
            await self._publish_state_change()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown application gracefully."""
        logger.info("Shutting down ATEM Director application")
        
        # Stop background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._engine_tick_task:
            self._engine_tick_task.cancel()
            try:
                await self._engine_tick_task
            except asyncio.CancelledError:
                pass
        
        if self._sync_stats_task:
            self._sync_stats_task.cancel()
            try:
                await self._sync_stats_task
            except asyncio.CancelledError:
                pass
        
        # Stop switching engine
        if self.switching_engine and self.state.engine_state == SwitchingState.RUNNING:
            self.switching_engine.stop()
        
        # Disconnect ATEM
        await self.atem_manager.disconnect()
        
        logger.info("Application shutdown complete")
    
    async def start_auto_switching(self) -> None:
        """Start automatic switching."""
        logger.info("Starting automatic switching")
        
        if not self.switching_engine:
            raise RuntimeError("Switching engine not initialized")
        
        if not self.atem_manager.is_connected:
            raise RuntimeError("ATEM device not connected")
        
        try:
            # Start engine
            self.switching_engine.start()
            
            # Start engine tick task
            self._engine_tick_task = asyncio.create_task(self._engine_tick_loop())
            
            # Create session
            async with self._state_lock:
                self.state.session_active = True
                self.state.session_started_at = datetime.now()
                self.state.session_stats = SwitchingSessionStats(
                    started_at=datetime.now()
                )
                self.state.auto_switch_enabled = True
                self.state.operation_mode = OperationMode.AUTO
            
            # Record event
            await self.storage.record_event(
                event_type="session_start",
                reason="Auto-switching started",
                is_success=True,
            )
            
            await self._publish_state_change()
            
        except Exception as e:
            logger.error("Failed to start auto-switching", error=str(e))
            
            async with self._state_lock:
                self.state.last_error = f"Failed to start auto-switching: {str(e)}"
                self.state.last_error_time = datetime.now()
                self.state.operation_mode = OperationMode.FAILSAFE
            
            await self._publish_state_change()
            raise
    
    async def stop_auto_switching(self) -> None:
        """Stop automatic switching."""
        logger.info("Stopping automatic switching")
        
        if self.switching_engine:
            self.switching_engine.stop()
        
        if self._engine_tick_task:
            self._engine_tick_task.cancel()
            try:
                await self._engine_tick_task
            except asyncio.CancelledError:
                pass
            finally:
                self._engine_tick_task = None
        
        async with self._state_lock:
            self.state.session_active = False
            self.state.auto_switch_enabled = False
            self.state.operation_mode = OperationMode.MANUAL
        
        # Record event
        await self.storage.record_event(
            event_type="session_stop",
            reason="Auto-switching stopped",
            is_success=True,
        )
        
        await self._publish_state_change()
    
    async def switch_to_input(self, input_index: int, reason: str = "manual") -> None:
        """Switch to specific input.
        
        Args:
            input_index: Input to switch to
            reason: Reason for switch (manual, skip, etc.)
        """
        logger.info("Manual switch requested", input_index=input_index, reason=reason)
        
        if not self.atem_manager.is_connected:
            raise RuntimeError("ATEM device not connected")
        
        # Validate input
        status = await self.atem_manager.get_status()
        if input_index < 1 or input_index > status.inputs_count:
            raise ValueError(f"Invalid input index {input_index}")
        
        # Get current state
        async with self._state_lock:
            old_input = self.state.switcher_state.program_input
        
        try:
            # Execute switch
            await self.atem_manager.set_program_input(input_index)
            
            # Update runtime state
            async with self._state_lock:
                self.state.switcher_state.program_input = input_index
                
                # Update camera states
                if old_input in self.state.camera_states:
                    self.state.camera_states[old_input].is_current_program = False
                
                if input_index in self.state.camera_states:
                    self.state.camera_states[input_index].is_current_program = True
                    self.state.camera_states[input_index].last_used_at = datetime.now()
            
            # Record statistics
            await self._record_switch(
                from_input=old_input,
                to_input=input_index,
                reason=reason,
                is_success=True,
            )
            
            logger.info("Switch successful", from_input=old_input, to_input=input_index)
            await self._publish_state_change()
            
        except Exception as e:
            logger.error("Switch failed", error=str(e))
            
            # Record failure
            await self._record_switch(
                from_input=old_input,
                to_input=input_index,
                reason=reason,
                is_success=False,
                error=str(e),
            )
            
            raise
    
    async def skip_current_camera(self) -> None:
        """Skip current camera (engine command)."""
        if not self.switching_engine:
            raise RuntimeError("Switching engine not initialized")
        
        logger.info("Skip current camera requested")
        self.switching_engine.handle_event(SwitchingEvent.SKIP_CURRENT)
    
    async def hold_current_camera(self, hold: bool = True) -> None:
        """Hold or release current camera.
        
        Args:
            hold: True to hold, False to release
        """
        if not self.switching_engine:
            raise RuntimeError("Switching engine not initialized")
        
        logger.info("Hold current camera", hold=hold)
        event = SwitchingEvent.HOLD_CURRENT if hold else SwitchingEvent.RELEASE_HOLD
        self.switching_engine.handle_event(event)
    
    def register_state_callback(self, callback: StateChangeCallback) -> None:
        """Register callback for state changes.
        
        Args:
            callback: Function to call on state change
        """
        self._state_callbacks.append(callback)
    
    async def get_dashboard_state(self) -> DashboardState:
        """Get complete dashboard state for UI.
        
        Returns:
            DashboardState with all current state
        """
        async with self._state_lock:
            return self.state.to_dashboard_state()
    
    # ========================================================================
    # Internal Callbacks
    # ========================================================================
    
    async def _on_atem_connection_change(self, state: ConnectionState) -> None:
        """Handle ATEM connection state change."""
        logger.info("ATEM connection state changed", state=state.value)
        
        async with self._state_lock:
            self.state.atem_status.state = state
            
            if state == ConnectionState.DISCONNECTED:
                self.state.operation_mode = OperationMode.FAILSAFE
                self.state.last_error = "ATEM device disconnected"
                self.state.last_error_time = datetime.now()
            elif state == ConnectionState.CONNECTED:
                self.state.last_error = None
                if self.state.auto_switch_enabled:
                    self.state.operation_mode = OperationMode.AUTO
                else:
                    self.state.operation_mode = OperationMode.MANUAL
        
        await self._publish_state_change()
    
    async def _on_atem_state_change(self, switcher_state: SwitcherState) -> None:
        """Handle ATEM switcher state change."""
        async with self._state_lock:
            old_program = self.state.switcher_state.program_input
            new_program = switcher_state.program_input
            
            self.state.switcher_state = switcher_state
            
            # Detect manual operator changes
            if old_program != new_program:
                logger.info(
                    "Manual operator switch detected",
                    from_input=old_program,
                    to_input=new_program,
                )
                
                # Update camera states
                if old_program in self.state.camera_states:
                    self.state.camera_states[old_program].is_current_program = False
                
                if new_program in self.state.camera_states:
                    self.state.camera_states[new_program].is_current_program = True
        
        await self._publish_state_change()
    
    def _on_engine_state_change(self, state: SwitchingState) -> None:
        """Handle switching engine state change."""
        logger.info("Engine state changed", state=state.value)
        
        # Sync to runtime state
        # Note: Non-async, will be synced by monitoring loop
    
    def _on_engine_switch(
        self,
        to_input: int,
        from_input: Optional[int] = None,
    ) -> None:
        """Handle switching engine switch event."""
        logger.info(
            "Engine initiated switch",
            from_input=from_input,
            to_input=to_input,
        )
        
        # Schedule async switch execution
        # Note: This is non-blocking callback
    
    # ========================================================================
    # Background Tasks
    # ========================================================================
    
    async def _monitoring_loop(self) -> None:
        """Monitor ATEM state and sync to runtime."""
        logger.info("Starting monitoring loop")
        
        try:
            while True:
                try:
                    # Get current device status
                    status = await self.atem_manager.get_status()
                    switcher_state = await self.atem_manager.get_switcher_state()
                    
                    async with self._state_lock:
                        self.state.atem_status = status
                        self.state.switcher_state = switcher_state
                        
                        # Update camera signal states
                        for input_idx, signal in switcher_state.input_signals.items():
                            if input_idx in self.state.camera_states:
                                self.state.camera_states[input_idx].has_signal = signal.has_signal
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning("Error in monitoring loop", error=str(e))
                    await asyncio.sleep(1.0)
        
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
    
    async def _engine_tick_loop(self) -> None:
        """Drive switching engine state machine."""
        logger.info("Starting engine tick loop")
        
        if not self.switching_engine:
            return
        
        try:
            while True:
                try:
                    # Get current program input from device
                    switcher_state = await self.atem_manager.get_switcher_state()
                    current_input = switcher_state.program_input
                    
                    # Update eligibility based on current signals
                    eligible_inputs = []
                    for input_idx, signal in switcher_state.input_signals.items():
                        camera = self.state.camera_states.get(input_idx)
                        
                        if (
                            signal.has_signal
                            and camera
                            and camera.enabled
                            and not camera.is_locked
                        ):
                            eligible_inputs.append(input_idx)
                    
                    # Tick engine
                    self.switching_engine.tick(
                        current_input=current_input,
                        eligible_inputs=eligible_inputs,
                        now=datetime.now(),
                    )
                    
                    # Get next action from engine
                    next_action = self.switching_engine.get_next_action()
                    
                    if next_action and next_action.input_index != current_input:
                        # Execute switch
                        await self.switch_to_input(
                            next_action.input_index,
                            reason="auto_switch",
                        )
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning("Error in engine tick", error=str(e))
                    await asyncio.sleep(1.0)
        
        except asyncio.CancelledError:
            logger.info("Engine tick loop cancelled")
    
    async def _stats_sync_loop(self) -> None:
        """Periodically sync statistics to storage."""
        logger.info("Starting stats sync loop")
        
        try:
            while True:
                try:
                    if self.state.session_active and self.state.session_stats:
                        # Sync current session stats
                        await self.storage.save_session_summary(
                            session_name=f"session_{self.state.session_started_at.timestamp()}",
                            total_switches=self.state.session_stats.total_switches,
                            total_duration=self.state.session_stats.total_hold_seconds,
                            auto_switch_enabled=self.state.auto_switch_enabled,
                            average_hold=self.state.session_stats.average_hold_seconds,
                        )
                    
                    await asyncio.sleep(30.0)
                    
                except Exception as e:
                    logger.warning("Error syncing stats", error=str(e))
                    await asyncio.sleep(60.0)
        
        except asyncio.CancelledError:
            logger.info("Stats sync loop cancelled")
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _sync_device_state(self) -> None:
        """Sync initial device state into runtime."""
        status = await self.atem_manager.get_status()
        switcher_state = await self.atem_manager.get_switcher_state()
        
        async with self._state_lock:
            self.state.atem_status = status
            self.state.switcher_state = switcher_state
    
    async def _initialize_camera_states(self, app_config: Any) -> None:
        """Initialize per-camera state."""
        status = await self.atem_manager.get_status()
        switcher_state = await self.atem_manager.get_switcher_state()
        
        async with self._state_lock:
            for i in range(1, status.inputs_count + 1):
                operator_state = await self.storage.get_input_operator_state(i)
                
                self.state.camera_states[i] = CameraState(
                    input_index=i,
                    enabled=operator_state.enabled if operator_state else True,
                    is_current_program=i == switcher_state.program_input,
                    is_current_preview=i == switcher_state.preview_input,
                    has_signal=switcher_state.input_signals.get(i, {}).has_signal,
                )
    
    async def _record_switch(
        self,
        from_input: int,
        to_input: int,
        reason: str,
        is_success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record switch event."""
        await self.storage.record_event(
            event_type="switch",
            from_input=from_input,
            to_input=to_input,
            reason=reason,
            is_success=is_success,
            error_message=error,
        )
        
        # Update session stats
        if self.state.session_active and self.state.session_stats:
            self.state.session_stats.total_switches += 1
            self.state.session_stats.last_switch_at = datetime.now()
            self.state.session_stats.last_switched_from = from_input
            self.state.session_stats.last_switched_to = to_input
        
        # Update camera stats
        if to_input in self.state.camera_states:
            camera = self.state.camera_states[to_input]
            camera.total_switches += 1
            camera.last_used_at = datetime.now()
    
    async def _publish_state_change(self) -> None:
        """Publish state change to all registered callbacks."""
        async with self._state_lock:
            dashboard_state = self.state.to_dashboard_state()
        
        for callback in self._state_callbacks:
            try:
                result = callback(dashboard_state)
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                logger.warning("Error in state callback", error=str(e))
    
    @staticmethod
    def _parse_switch_mode(mode_str: str) -> SwitchMode:
        """Parse switch mode string to enum."""
        mode_map = {
            "pure_random": SwitchMode.PURE_RANDOM,
            "balanced_random": SwitchMode.BALANCED_RANDOM,
            "weighted_random": SwitchMode.WEIGHTED_RANDOM,
            "round_robin_random": SwitchMode.ROUND_ROBIN_RANDOM,
        }
        return mode_map.get(mode_str, SwitchMode.BALANCED_RANDOM)
