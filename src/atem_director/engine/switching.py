"""Switching engine - core domain logic for camera switching automation.

This module implements an explicit state machine for managing automated camera
switching with support for multiple switch modes, safety rules, and operator
control. Pure domain logic separated from infrastructure concerns.

Key abstractions:
- SwitchingState: Explicit state machine states
- SwitchingEvent: Events that drive state transitions
- InputEligibility: Determines which inputs can be switched to
- SwitchMode: Different switching algorithms
- SwitchingEngine: Core state machine and business logic
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Set, List, Dict, Tuple, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import random

from atem_director.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# State and Event Enums
# ============================================================================

class SwitchingState(str, Enum):
    """Explicit switching engine states."""
    IDLE = "idle"  # Waiting for start
    READY = "ready"  # Configured and ready to switch
    RUNNING = "running"  # Actively switching cameras
    PAUSED = "paused"  # Paused, will resume with next start
    LOCKED = "locked"  # Current input locked, no switching
    RECONNECTING = "reconnecting"  # Device reconnecting
    ERROR = "error"  # Fatal error state


class SwitchingEvent(str, Enum):
    """Events that drive state transitions."""
    START = "start"
    STOP = "stop"
    TICK = "tick"
    SKIP_CURRENT = "skip_current"  # Switch immediately
    SKIP_NEXT = "skip_next"  # Extend current, re-randomize next
    EXTEND_TIME = "extend_time"  # Add time to current interval
    HOLD_CURRENT = "hold_current"  # Pause switching, stay on current
    LOCK_CURRENT = "lock_current"  # Lock current input for duration
    RELEASE_LOCK = "release_lock"
    SIGNAL_LOST = "signal_lost"
    SIGNAL_RESTORED = "signal_restored"
    INPUT_ENABLED = "input_enabled"  # Operator enabled input
    INPUT_DISABLED = "input_disabled"  # Operator disabled input
    MANUAL_SWITCH_DETECTED = "manual_switch_detected"
    DISCONNECT = "disconnect"  # Device disconnected
    RECONNECT = "reconnect"  # Device reconnected


# ============================================================================
# Safety Rules and Eligibility
# ============================================================================

@dataclass
class InputEligibility:
    """Determines whether an input can be switched to."""
    
    # Safety checks
    has_signal: bool = False
    operator_enabled: bool = True
    passes_repeat_check: bool = True
    passes_cooldown: bool = True
    
    @property
    def is_eligible(self) -> bool:
        """Input is eligible if all checks pass."""
        return (
            self.has_signal
            and self.operator_enabled
            and self.passes_repeat_check
            and self.passes_cooldown
        )


@dataclass
class SwitchingConfig:
    """Switching engine configuration."""
    
    # Intervals for automatic switching (milliseconds)
    interval_pool: List[int] = field(
        default_factory=lambda: [30000, 60000, 90000, 120000, 150000]
    )
    
    # Enable/disable intervals dynamically
    enabled_intervals: Set[int] = field(default_factory=set)
    
    # Switching mode
    switch_mode: 'SwitchMode' = None  # Set at init
    
    # Safety settings
    avoid_repeat_same_input: bool = True
    same_input_cooldown_ms: int = 2000
    enable_signal_loss_protection: bool = True
    
    # Manual override handling
    respect_manual_override: bool = True
    manual_override_duration_ms: int = 30000
    
    def __post_init__(self) -> None:
        """Initialize enabled intervals from pool."""
        if not self.enabled_intervals:
            self.enabled_intervals = set(self.interval_pool)


@dataclass
class InputState:
    """State of a single input."""
    
    input_index: int
    has_signal: bool = False
    operator_enabled: bool = True
    last_switched_at: Optional[datetime] = None
    last_switch_duration_ms: int = 0


@dataclass
class LockState:
    """State of a locked input."""
    
    locked_input: int
    locked_until: datetime
    reason: str = "manual_lock"
    
    @property
    def is_active(self) -> bool:
        """Check if lock is still active."""
        return datetime.now() < self.locked_until


# ============================================================================
# Switch Modes
# ============================================================================

class SwitchMode(ABC):
    """Abstract base class for switching algorithms."""
    
    @abstractmethod
    def select_next_input(
        self,
        eligible_inputs: List[int],
        current_input: int,
        state_map: Dict[int, InputState],
    ) -> int:
        """Select next input to switch to.
        
        Args:
            eligible_inputs: List of input indices that can be switched to
            current_input: Currently active input index
            state_map: Map of input states
            
        Returns:
            Selected input index
            
        Raises:
            ValueError: If no eligible inputs
        """
        pass
    
    @abstractmethod
    def select_next_interval(
        self,
        enabled_intervals: Set[int],
    ) -> int:
        """Select next switching interval.
        
        Args:
            enabled_intervals: Set of enabled interval durations (ms)
            
        Returns:
            Selected interval in milliseconds
        """
        pass


class PureRandomMode(SwitchMode):
    """Pure random selection from eligible inputs."""
    
    def select_next_input(
        self,
        eligible_inputs: List[int],
        current_input: int,
        state_map: Dict[int, InputState],
    ) -> int:
        """Randomly select from eligible inputs."""
        if not eligible_inputs:
            raise ValueError("No eligible inputs available")
        
        return random.choice(eligible_inputs)
    
    def select_next_interval(
        self,
        enabled_intervals: Set[int],
    ) -> int:
        """Randomly select interval."""
        if not enabled_intervals:
            raise ValueError("No enabled intervals")
        
        return random.choice(list(enabled_intervals))


class BalancedRandomMode(SwitchMode):
    """Random selection avoiding immediate repeats."""
    
    def select_next_input(
        self,
        eligible_inputs: List[int],
        current_input: int,
        state_map: Dict[int, InputState],
    ) -> int:
        """Select from eligible inputs, avoiding current if possible."""
        if not eligible_inputs:
            raise ValueError("No eligible inputs available")
        
        # Remove current input from candidates if alternatives exist
        candidates = [i for i in eligible_inputs if i != current_input]
        
        if candidates:
            return random.choice(candidates)
        else:
            # Only current input eligible
            return eligible_inputs[0]
    
    def select_next_interval(
        self,
        enabled_intervals: Set[int],
    ) -> int:
        """Randomly select interval."""
        if not enabled_intervals:
            raise ValueError("No enabled intervals")
        
        return random.choice(list(enabled_intervals))


class WeightedRandomMode(SwitchMode):
    """Random selection weighted by switch frequency."""
    
    def __init__(self, weight_by_frequency: bool = True) -> None:
        """Initialize weighted random mode.
        
        Args:
            weight_by_frequency: If True, less-used inputs are weighted higher
        """
        self.weight_by_frequency = weight_by_frequency
    
    def select_next_input(
        self,
        eligible_inputs: List[int],
        current_input: int,
        state_map: Dict[int, InputState],
    ) -> int:
        """Select input weighted by switch frequency."""
        if not eligible_inputs:
            raise ValueError("No eligible inputs available")
        
        if not self.weight_by_frequency or len(eligible_inputs) == 1:
            return random.choice(eligible_inputs)
        
        # Calculate weights based on how recently each was used
        weights = []
        now = datetime.now()
        
        for input_idx in eligible_inputs:
            state = state_map.get(input_idx)
            if state and state.last_switched_at:
                # Weight = time since last switch (higher = less recently used)
                time_since = (now - state.last_switched_at).total_seconds()
                weights.append(time_since)
            else:
                # Never used = highest weight
                weights.append(float('inf'))
        
        # Normalize weights
        min_weight = min(weights)
        if min_weight == float('inf'):
            normalized = [1.0] * len(weights)
        else:
            normalized = [w - min_weight + 1 for w in weights]
        
        # Weighted random selection
        return random.choices(eligible_inputs, weights=normalized, k=1)[0]
    
    def select_next_interval(
        self,
        enabled_intervals: Set[int],
    ) -> int:
        """Randomly select interval."""
        if not enabled_intervals:
            raise ValueError("No enabled intervals")
        
        return random.choice(list(enabled_intervals))


class RoundRobinRandomMode(SwitchMode):
    """Round-robin through inputs with random intervals."""
    
    def __init__(self) -> None:
        """Initialize round-robin mode."""
        self.round_robin_index = 0
    
    def select_next_input(
        self,
        eligible_inputs: List[int],
        current_input: int,
        state_map: Dict[int, InputState],
    ) -> int:
        """Select input in round-robin order."""
        if not eligible_inputs:
            raise ValueError("No eligible inputs available")
        
        sorted_inputs = sorted(eligible_inputs)
        current_index = self.round_robin_index % len(sorted_inputs)
        selected = sorted_inputs[current_index]
        
        # Advance index for next time
        self.round_robin_index = (current_index + 1) % len(sorted_inputs)
        
        return selected
    
    def select_next_interval(
        self,
        enabled_intervals: Set[int],
    ) -> int:
        """Randomly select interval."""
        if not enabled_intervals:
            raise ValueError("No enabled intervals")
        
        return random.choice(list(enabled_intervals))


# ============================================================================
# Main Switching Engine
# ============================================================================

@dataclass
class SwitchingEngineState:
    """Internal state snapshot for the switching engine."""
    
    state: SwitchingState
    current_input: int
    next_input: Optional[int] = None
    time_until_switch_ms: int = 0
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    eligible_inputs: List[int] = field(default_factory=list)


class SwitchingEngine:
    """Core switching engine state machine.
    
    Pure domain logic for automated camera switching with explicit state
    machine, safety rules, and multiple switching modes.
    """
    
    def __init__(
        self,
        config: SwitchingConfig,
        switch_mode: Optional[SwitchMode] = None,
    ) -> None:
        """Initialize switching engine.
        
        Args:
            config: Switching configuration
            switch_mode: Switching mode (defaults to BalancedRandomMode)
        """
        self.config = config
        self.config.switch_mode = switch_mode or BalancedRandomMode()
        
        # State machine
        self._state = SwitchingState.IDLE
        self._current_input = 0
        self._next_input: Optional[int] = None
        self._countdown_ms = 0
        
        # Input states
        self._input_states: Dict[int, InputState] = {}
        
        # Lock state
        self._lock_state: Optional[LockState] = None
        
        # Manual override tracking
        self._manual_override_until: Optional[datetime] = None
        
        # Callbacks
        self._switch_callbacks: List[Callable[[int, int], None]] = []
        self._state_callbacks: List[Callable[[SwitchingState], None]] = []
        
        # Statistics
        self._total_switches = 0
        self._last_state_change_at = datetime.now()
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def handle_event(self, event: SwitchingEvent, **kwargs) -> None:
        """Handle a switching event.
        
        Args:
            event: The event to handle
            **kwargs: Event-specific arguments
        """
        logger.debug("Handling switching event", evt=event.value, state=self._state.value)
        
        if event == SwitchingEvent.START:
            self._handle_start()
        elif event == SwitchingEvent.STOP:
            self._handle_stop()
        elif event == SwitchingEvent.TICK:
            self._handle_tick()
        elif event == SwitchingEvent.SKIP_CURRENT:
            self._handle_skip_current()
        elif event == SwitchingEvent.SKIP_NEXT:
            self._handle_skip_next()
        elif event == SwitchingEvent.EXTEND_TIME:
            extend_ms = kwargs.get("duration_ms", 30000)
            self._handle_extend_time(extend_ms)
        elif event == SwitchingEvent.HOLD_CURRENT:
            self._handle_hold_current()
        elif event == SwitchingEvent.LOCK_CURRENT:
            duration_ms = kwargs.get("duration_ms", 10000)
            self._handle_lock_current(duration_ms)
        elif event == SwitchingEvent.RELEASE_LOCK:
            self._handle_release_lock()
        elif event == SwitchingEvent.SIGNAL_LOST:
            input_idx = kwargs.get("input_index")
            self._handle_signal_lost(input_idx)
        elif event == SwitchingEvent.SIGNAL_RESTORED:
            input_idx = kwargs.get("input_index")
            self._handle_signal_restored(input_idx)
        elif event == SwitchingEvent.INPUT_ENABLED:
            input_idx = kwargs.get("input_index")
            self._handle_input_enabled(input_idx)
        elif event == SwitchingEvent.INPUT_DISABLED:
            input_idx = kwargs.get("input_index")
            self._handle_input_disabled(input_idx)
        elif event == SwitchingEvent.MANUAL_SWITCH_DETECTED:
            input_idx = kwargs.get("input_index")
            self._handle_manual_switch(input_idx)
        elif event == SwitchingEvent.DISCONNECT:
            self._handle_disconnect()
        elif event == SwitchingEvent.RECONNECT:
            self._handle_reconnect()
    
    def _handle_start(self) -> None:
        """Handle START event."""
        if self._state not in (SwitchingState.IDLE, SwitchingState.PAUSED):
            logger.warning("Cannot start from state", state=self._state.value)
            return
        
        self._set_state(SwitchingState.READY)
        
        # Initialize input states if needed
        if not self._input_states:
            for i in range(1, 9):  # Assume 8 inputs
                self._input_states[i] = InputState(input_index=i)
        
        # Transition to RUNNING and schedule first switch
        self._set_state(SwitchingState.RUNNING)
        self._schedule_next_switch()
    
    def _handle_stop(self) -> None:
        """Handle STOP event."""
        self._set_state(SwitchingState.IDLE)
        self._countdown_ms = 0
        self._next_input = None
        self._release_lock()
    
    def _handle_tick(self) -> None:
        """Handle TICK event (time increment)."""
        if self._state != SwitchingState.RUNNING:
            return
        
        # Check if lock expired
        if self._lock_state and not self._lock_state.is_active:
            self._release_lock()
        
        # Decrement countdown
        if self._countdown_ms > 0:
            self._countdown_ms = max(0, self._countdown_ms - 1000)
        
        # Check for switch
        if self._countdown_ms == 0 and self._next_input is not None:
            self._perform_switch(self._next_input)
            self._schedule_next_switch()
    
    def _handle_skip_current(self) -> None:
        """Handle SKIP_CURRENT event (switch immediately)."""
        if self._state != SwitchingState.RUNNING:
            logger.warning("Cannot skip current - not running")
            return
        
        eligible = self._get_eligible_inputs()
        if not eligible:
            logger.warning("No eligible inputs for skip")
            return
        
        next_input = self.config.switch_mode.select_next_input(
            eligible, self._current_input, self._input_states
        )
        
        self._perform_switch(next_input)
        self._schedule_next_switch()
    
    def _handle_skip_next(self) -> None:
        """Handle SKIP_NEXT event (extend current, re-randomize next)."""
        if self._state != SwitchingState.RUNNING:
            logger.warning("Cannot skip next - not running")
            return
        
        # Reset countdown to delay next switch
        self._countdown_ms = (
            self.config.switch_mode.select_next_interval(
                self.config.enabled_intervals
            )
        )
        self._next_input = None
    
    def _handle_extend_time(self, extend_ms: int) -> None:
        """Handle EXTEND_TIME event."""
        if self._state != SwitchingState.RUNNING:
            logger.warning("Cannot extend time - not running")
            return
        
        self._countdown_ms += extend_ms
        logger.info("Extended interval", extend_ms=extend_ms, new_countdown_ms=self._countdown_ms)
    
    def _handle_hold_current(self) -> None:
        """Handle HOLD_CURRENT event (pause switching)."""
        if self._state == SwitchingState.RUNNING:
            self._set_state(SwitchingState.PAUSED)
        elif self._state == SwitchingState.PAUSED:
            self._set_state(SwitchingState.RUNNING)
    
    def _handle_lock_current(self, duration_ms: int) -> None:
        """Handle LOCK_CURRENT event."""
        if self._current_input == 0:
            logger.warning("Cannot lock - no current input")
            return
        
        locked_until = datetime.now() + timedelta(milliseconds=duration_ms)
        self._lock_state = LockState(
            locked_input=self._current_input,
            locked_until=locked_until,
            reason="manual_lock",
        )
        
        logger.info("Locked input", input_index=self._current_input, duration_ms=duration_ms)
    
    def _handle_release_lock(self) -> None:
        """Handle RELEASE_LOCK event."""
        self._release_lock()
    
    def _handle_signal_lost(self, input_idx: Optional[int]) -> None:
        """Handle SIGNAL_LOST event."""
        if input_idx is None:
            return
        
        if input_idx not in self._input_states:
            return
        
        self._input_states[input_idx].has_signal = False
        logger.warning("Signal lost", input_index=input_idx)
        
        # If current input lost signal, switch immediately
        if input_idx == self._current_input and self.config.enable_signal_loss_protection:
            if self._state == SwitchingState.RUNNING:
                self._handle_skip_current()
    
    def _handle_signal_restored(self, input_idx: Optional[int]) -> None:
        """Handle SIGNAL_RESTORED event."""
        if input_idx is None:
            return
        
        if input_idx not in self._input_states:
            return
        
        self._input_states[input_idx].has_signal = True
        logger.info("Signal restored", input_index=input_idx)
    
    def _handle_input_enabled(self, input_idx: Optional[int]) -> None:
        """Handle INPUT_ENABLED event."""
        if input_idx is None:
            return
        
        if input_idx not in self._input_states:
            self._input_states[input_idx] = InputState(input_index=input_idx)
        
        self._input_states[input_idx].operator_enabled = True
        logger.info("Input enabled", input_index=input_idx)
    
    def _handle_input_disabled(self, input_idx: Optional[int]) -> None:
        """Handle INPUT_DISABLED event."""
        if input_idx is None:
            return
        
        if input_idx not in self._input_states:
            self._input_states[input_idx] = InputState(input_index=input_idx)
        
        self._input_states[input_idx].operator_enabled = False
        logger.info("Input disabled", input_index=input_idx)
        
        # If disabled input is current and no lock, switch immediately
        if (input_idx == self._current_input
            and self._state == SwitchingState.RUNNING
            and not self._is_locked()):
            self._handle_skip_current()
    
    def _handle_manual_switch(self, input_idx: Optional[int]) -> None:
        """Handle manual switch detected (operator switched via device)."""
        if input_idx is None:
            return
        
        self._current_input = input_idx
        
        # Override auto-switching temporarily
        if self.config.respect_manual_override:
            self._manual_override_until = (
                datetime.now() +
                timedelta(milliseconds=self.config.manual_override_duration_ms)
            )
            self._countdown_ms = self.config.manual_override_duration_ms
        
        logger.info("Manual switch detected", input_index=input_idx)
    
    def _handle_disconnect(self) -> None:
        """Handle DISCONNECT event."""
        old_state = self._state
        self._set_state(SwitchingState.RECONNECTING)
        logger.warning("Switching engine disconnected")
    
    def _handle_reconnect(self) -> None:
        """Handle RECONNECT event."""
        if self._state == SwitchingState.RECONNECTING:
            self._set_state(SwitchingState.RUNNING)
        
        logger.info("Switching engine reconnected")
    
    # ========================================================================
    # Core Switching Logic
    # ========================================================================
    
    def _get_eligible_inputs(self) -> List[int]:
        """Get list of eligible inputs.
        
        Eligible = has_signal + operator_enabled + passes_safety_rules
        
        Returns:
            List of eligible input indices
        """
        eligible = []
        now = datetime.now()
        
        for input_idx, state in self._input_states.items():
            # Must have signal
            if not state.has_signal:
                continue
            
            # Must be operator-enabled
            if not state.operator_enabled:
                continue
            
            # Tentatively exclude the current input to avoid repeats;
            # we will add it back below if nothing else is available.
            if self.config.avoid_repeat_same_input and input_idx == self._current_input:
                continue

            eligible.append(input_idx)

        # Fallback: if no alternatives exist, allow the current input to repeat.
        if not eligible and self._current_input in self._input_states:
            current_state = self._input_states[self._current_input]
            if current_state.has_signal and current_state.operator_enabled:
                eligible.append(self._current_input)

        return eligible
    
    def _schedule_next_switch(self) -> None:
        """Schedule the next switch after interval."""
        eligible = self._get_eligible_inputs()
        
        if not eligible:
            # No eligible inputs - wait and try again
            logger.warning("No eligible inputs available, will retry")
            self._next_input = None
            self._countdown_ms = 5000  # Try again in 5 seconds
            return
        
        # Select next input
        self._next_input = self.config.switch_mode.select_next_input(
            eligible, self._current_input, self._input_states
        )
        
        # Select interval
        self._countdown_ms = self.config.switch_mode.select_next_interval(
            self.config.enabled_intervals
        )
        
        logger.debug(
            "Scheduled next switch",
            next_input=self._next_input,
            interval_ms=self._countdown_ms,
        )
    
    def _perform_switch(self, new_input: int) -> None:
        """Perform a switch to new input.
        
        Args:
            new_input: Input index to switch to
        """
        old_input = self._current_input
        
        # Re-validate eligibility at switch time
        eligible = self._get_eligible_inputs()
        if new_input not in eligible:
            logger.warning(
                "Target input no longer eligible",
                input_index=new_input,
                eligible=eligible,
            )
            return
        
        # Perform the switch
        self._current_input = new_input
        
        # Update input state
        now = datetime.now()
        if new_input in self._input_states:
            state = self._input_states[new_input]
            if state.last_switched_at:
                state.last_switch_duration_ms = int(
                    (now - state.last_switched_at).total_seconds() * 1000
                )
            state.last_switched_at = now
        
        self._total_switches += 1
        
        logger.info(
            "Performing switch",
            from_input=old_input,
            to_input=new_input,
            total_switches=self._total_switches,
        )
        
        # Notify callbacks
        for callback in self._switch_callbacks:
            try:
                callback(old_input, new_input)
            except Exception as e:
                logger.warning("Error in switch callback", error=str(e))
    
    # ========================================================================
    # State Management
    # ========================================================================
    
    def _set_state(self, new_state: SwitchingState) -> None:
        """Set switching state.
        
        Args:
            new_state: New state
        """
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._last_state_change_at = datetime.now()
            
            logger.info("State transition", from_state=old_state.value, to_state=new_state.value)
            
            # Notify callbacks
            for callback in self._state_callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.warning("Error in state callback", error=str(e))
    
    def _release_lock(self) -> None:
        """Release current lock if active."""
        if self._lock_state:
            logger.info("Lock released", was_locked_input=self._lock_state.locked_input)
            self._lock_state = None
    
    def _is_locked(self) -> bool:
        """Check if current input is locked."""
        return self._lock_state is not None and self._lock_state.is_active
    
    # ========================================================================
    # State Queries
    # ========================================================================
    
    def get_state(self) -> SwitchingEngineState:
        """Get current engine state snapshot.
        
        Returns:
            Current state snapshot
        """
        return SwitchingEngineState(
            state=self._state,
            current_input=self._current_input,
            next_input=self._next_input,
            time_until_switch_ms=self._countdown_ms,
            is_locked=self._is_locked(),
            locked_until=self._lock_state.locked_until if self._lock_state else None,
            eligible_inputs=self._get_eligible_inputs(),
        )
    
    # ------------------------------------------------------------------
    # Convenience methods (used by ApplicationOrchestrator)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Convenience: fire the START event to begin auto-switching."""
        self.handle_event(SwitchingEvent.START)

    def stop(self) -> None:
        """Convenience: fire the STOP event to halt auto-switching."""
        self.handle_event(SwitchingEvent.STOP)

    def on_state_change(self, callback) -> None:
        """Alias for register_state_callback (matches orchestrator API)."""
        self.register_state_callback(callback)

    def on_switch(self, callback) -> None:
        """Alias for register_switch_callback (matches orchestrator API)."""
        self.register_switch_callback(callback)

    # ------------------------------------------------------------------

    def register_switch_callback(self, callback: Callable[[int, int], None]) -> None:
        """Register callback for switch events.
        
        Args:
            callback: Function(old_input, new_input)
        """
        self._switch_callbacks.append(callback)
    
    def register_state_callback(self, callback: Callable[[SwitchingState], None]) -> None:
        """Register callback for state changes.
        
        Args:
            callback: Function(new_state)
        """
        self._state_callbacks.append(callback)
    
    def set_input_signals(self, signals: Dict[int, bool]) -> None:
        """Update input signal states.
        
        Args:
            signals: Dict of input_index -> has_signal
        """
        for input_idx, has_signal in signals.items():
            if input_idx not in self._input_states:
                self._input_states[input_idx] = InputState(input_index=input_idx)
            
            old_has_signal = self._input_states[input_idx].has_signal
            self._input_states[input_idx].has_signal = has_signal
            
            # Trigger events for changes
            if has_signal and not old_has_signal:
                self.handle_event(SwitchingEvent.SIGNAL_RESTORED, input_index=input_idx)
            elif not has_signal and old_has_signal:
                self.handle_event(SwitchingEvent.SIGNAL_LOST, input_index=input_idx)
    
    @property
    def is_running(self) -> bool:
        """Check if engine is actively switching."""
        return self._state in (SwitchingState.RUNNING, SwitchingState.LOCKED)
    
    @property
    def current_input(self) -> int:
        """Get current input."""
        return self._current_input
    
    @property
    def eligible_inputs(self) -> List[int]:
        """Get currently eligible inputs."""
        return self._get_eligible_inputs()
    
    @property
    def total_switches(self) -> int:
        """Get total switches performed."""
        return self._total_switches
