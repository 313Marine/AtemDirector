"""Unit tests for switching engine state machine."""
import pytest
from datetime import datetime, timedelta

from atem_director.engine.switching import (
    SwitchingEngine,
    SwitchingConfig,
    SwitchingState,
    SwitchingEvent,
    InputState,
    PureRandomMode,
    BalancedRandomMode,
    WeightedRandomMode,
    RoundRobinRandomMode,
)


class TestSwitchingEngineBasic:
    """Basic state machine tests."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig()
        self.engine = SwitchingEngine(self.config, PureRandomMode())
        
        # Set up 4 inputs with signals
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_initial_state_is_idle(self):
        """Engine starts in IDLE state."""
        assert self.engine._state == SwitchingState.IDLE
        assert self.engine.current_input == 0
        assert not self.engine.is_running
    
    def test_start_transitions_to_running(self):
        """START event transitions IDLE -> READY -> RUNNING."""
        self.engine.handle_event(SwitchingEvent.START)
        assert self.engine._state == SwitchingState.RUNNING
        assert self.engine.is_running
    
    def test_stop_transitions_to_idle(self):
        """STOP event transitions back to IDLE."""
        self.engine.handle_event(SwitchingEvent.START)
        assert self.engine._state == SwitchingState.RUNNING
        
        self.engine.handle_event(SwitchingEvent.STOP)
        assert self.engine._state == SwitchingState.IDLE
        assert not self.engine.is_running
    
    def test_cannot_start_twice(self):
        """Cannot start when already running."""
        self.engine.handle_event(SwitchingEvent.START)
        state_before = self.engine._state
        
        self.engine.handle_event(SwitchingEvent.START)
        # State should not change
        assert self.engine._state == state_before


class TestSwitchingLogic:
    """Test core switching logic."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig(
            interval_pool=[1000, 2000, 3000],
        )
        self.engine = SwitchingEngine(self.config, BalancedRandomMode())
        
        # Set up 4 inputs with signals
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
        
        # Track switches
        self.switches = []
        self.engine.register_switch_callback(
            lambda old, new: self.switches.append((old, new))
        )
    
    def test_eligible_inputs_requires_signal(self):
        """Inputs without signal are not eligible."""
        self.engine._input_states[1].has_signal = False
        
        eligible = self.engine._get_eligible_inputs()
        assert 1 not in eligible
        assert len(eligible) == 3  # Only 2, 3, 4
    
    def test_eligible_inputs_respects_operator_disable(self):
        """Operator-disabled inputs are not eligible."""
        self.engine._input_states[2].operator_enabled = False
        
        eligible = self.engine._get_eligible_inputs()
        assert 2 not in eligible
        assert len(eligible) == 3  # Only 1, 3, 4
    
    def test_skip_current_switches_immediately(self):
        """SKIP_CURRENT switches to next immediately."""
        self.engine.handle_event(SwitchingEvent.START)
        original_input = self.engine.current_input
        
        self.engine.handle_event(SwitchingEvent.SKIP_CURRENT)
        
        # Should have switched
        assert len(self.switches) > 0
        assert self.engine.current_input != original_input
    
    def test_no_eligible_inputs_does_not_crash(self):
        """Engine handles no-eligible-inputs gracefully."""
        # Disable all inputs
        for i in range(1, 5):
            self.engine._input_states[i].operator_enabled = False
        
        self.engine.handle_event(SwitchingEvent.START)
        self.engine.handle_event(SwitchingEvent.SKIP_CURRENT)
        
        # Should not crash, no switch performed
        assert len(self.switches) == 0
    
    def test_single_eligible_input_switches_to_it(self):
        """With only one eligible input, switches to it."""
        # Disable inputs 2, 3, 4
        for i in range(2, 5):
            self.engine._input_states[i].operator_enabled = False
        
        self.engine.handle_event(SwitchingEvent.START)
        self.engine.handle_event(SwitchingEvent.SKIP_CURRENT)
        
        # Should switch to input 1
        assert len(self.switches) > 0
        assert self.engine.current_input == 1
    
    def test_total_switches_counter(self):
        """Total switches counter increments correctly."""
        self.engine.handle_event(SwitchingEvent.START)
        
        assert self.engine.total_switches == 0
        
        self.engine.handle_event(SwitchingEvent.SKIP_CURRENT)
        assert self.engine.total_switches == 1
        
        self.engine.handle_event(SwitchingEvent.SKIP_CURRENT)
        assert self.engine.total_switches == 2


class TestSafetyRules:
    """Test safety rules and restrictions."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig(
            avoid_repeat_same_input=True,
            same_input_cooldown_ms=1000,
        )
        self.engine = SwitchingEngine(self.config, PureRandomMode())
        
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_avoid_repeat_same_input(self):
        """Avoids switching to same input unless necessary."""
        # Set current input to 1
        self.engine._current_input = 1

        # Disable inputs 3 and 4, but leave input 2 enabled.
        # With another option available, input 1 (current) should be excluded.
        for i in range(3, 5):
            self.engine._input_states[i].operator_enabled = False

        eligible = self.engine._get_eligible_inputs()

        # Input 1 should be excluded because input 2 is still available
        assert 1 not in eligible
        assert 2 in eligible
    
    def test_single_input_available_allows_repeat(self):
        """When only one input available, allows repeat."""
        self.engine._current_input = 1
        
        # Disable all but input 1
        for i in range(2, 5):
            self.engine._input_states[i].operator_enabled = False
        
        eligible = self.engine._get_eligible_inputs()
        
        # Input 1 should be included as only option
        assert 1 in eligible
        assert len(eligible) == 1
    
    def test_signal_loss_triggers_switch(self):
        """Signal loss on current input triggers switch."""
        self.engine.handle_event(SwitchingEvent.START)
        self.engine._current_input = 1
        
        switches_before = self.engine.total_switches
        
        # Simulate signal loss on input 1
        self.engine.handle_event(SwitchingEvent.SIGNAL_LOST, input_index=1)
        
        # Should have switched away
        assert self.engine.total_switches > switches_before
        assert self.engine.current_input != 1
    
    def test_signal_loss_on_other_input_no_switch(self):
        """Signal loss on non-current input doesn't trigger switch."""
        self.engine.handle_event(SwitchingEvent.START)
        self.engine._current_input = 1
        
        switches_before = self.engine.total_switches
        
        # Simulate signal loss on input 2
        self.engine.handle_event(SwitchingEvent.SIGNAL_LOST, input_index=2)
        
        # Should not have switched immediately
        assert self.engine.current_input == 1
    
    def test_input_disable_triggers_switch_if_current(self):
        """Disabling current input triggers switch."""
        self.engine.handle_event(SwitchingEvent.START)
        self.engine._current_input = 1
        
        switches_before = self.engine.total_switches
        
        # Disable input 1
        self.engine.handle_event(SwitchingEvent.INPUT_DISABLED, input_index=1)
        
        # Should have switched away
        assert self.engine.total_switches > switches_before
        assert self.engine.current_input != 1


class TestLocking:
    """Test input locking."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig()
        self.engine = SwitchingEngine(self.config, PureRandomMode())
        
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_lock_current_input(self):
        """Can lock current input."""
        self.engine._current_input = 1
        
        self.engine.handle_event(SwitchingEvent.LOCK_CURRENT, duration_ms=5000)
        
        assert self.engine._lock_state is not None
        assert self.engine._lock_state.locked_input == 1
        assert self.engine._is_locked()
    
    def test_lock_expires(self):
        """Lock expires after duration."""
        self.engine._current_input = 1
        
        # Lock for -1000ms (already expired)
        expired_time = datetime.now() - timedelta(milliseconds=1000)
        self.engine._lock_state = self.engine._lock_state or None
        
        from atem_director.engine.switching import LockState
        self.engine._lock_state = LockState(
            locked_input=1,
            locked_until=expired_time,
        )
        
        assert not self.engine._is_locked()
    
    def test_release_lock(self):
        """Can manually release lock."""
        self.engine._current_input = 1
        self.engine.handle_event(SwitchingEvent.LOCK_CURRENT, duration_ms=5000)
        
        assert self.engine._is_locked()
        
        self.engine.handle_event(SwitchingEvent.RELEASE_LOCK)
        
        assert not self.engine._is_locked()


class TestPauseResume:
    """Test pause/resume functionality."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig()
        self.engine = SwitchingEngine(self.config, PureRandomMode())
        
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_hold_current_pauses(self):
        """HOLD_CURRENT pauses switching."""
        self.engine.handle_event(SwitchingEvent.START)
        assert self.engine._state == SwitchingState.RUNNING
        
        self.engine.handle_event(SwitchingEvent.HOLD_CURRENT)
        assert self.engine._state == SwitchingState.PAUSED
    
    def test_hold_current_resumes(self):
        """HOLD_CURRENT resumes from paused."""
        self.engine.handle_event(SwitchingEvent.START)
        self.engine.handle_event(SwitchingEvent.HOLD_CURRENT)
        assert self.engine._state == SwitchingState.PAUSED
        
        self.engine.handle_event(SwitchingEvent.HOLD_CURRENT)
        assert self.engine._state == SwitchingState.RUNNING


class TestSwitchingModes:
    """Test different switching modes."""
    
    def setup_method(self):
        """Set up test engine with 4 inputs."""
        self.config = SwitchingConfig()
        
        for i in range(1, 5):
            self.engine_input_states = {}
            self.engine_input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_pure_random_mode(self):
        """Pure random mode selects randomly."""
        mode = PureRandomMode()
        eligible = [1, 2, 3, 4]
        
        # Run multiple times to verify randomness
        selections = []
        for _ in range(20):
            selected = mode.select_next_input(eligible, 0, {})
            selections.append(selected)
        
        # Should have multiple different selections
        assert len(set(selections)) > 1
    
    def test_balanced_random_mode_avoids_current(self):
        """Balanced random avoids current if alternatives exist."""
        mode = BalancedRandomMode()
        eligible = [1, 2, 3, 4]
        
        # Run multiple times
        selections = []
        for _ in range(20):
            selected = mode.select_next_input(eligible, 1, {})
            selections.append(selected)
        
        # Should rarely select input 1 (current)
        count_1 = selections.count(1)
        total = len(selections)
        
        # Expect input 1 selected much less than 1/4 of the time
        assert count_1 / total < 0.25
    
    def test_round_robin_mode_cycles(self):
        """Round robin mode cycles through inputs."""
        mode = RoundRobinRandomMode()
        eligible = [1, 2, 3, 4]
        
        selections = []
        for _ in range(8):
            selected = mode.select_next_input(eligible, 0, {})
            selections.append(selected)
        
        # Should cycle: 1, 2, 3, 4, 1, 2, 3, 4
        expected = [1, 2, 3, 4, 1, 2, 3, 4]
        assert selections == expected


class TestEventHandling:
    """Test event handling edge cases."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig()
        self.engine = SwitchingEngine(self.config, PureRandomMode())
        
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_events_ignored_in_idle(self):
        """Certain events ignored when idle."""
        # TICK in IDLE should do nothing
        self.engine.handle_event(SwitchingEvent.TICK)
        assert self.engine._state == SwitchingState.IDLE
    
    def test_skip_next_extends_interval(self):
        """SKIP_NEXT extends current interval."""
        self.engine.handle_event(SwitchingEvent.START)
        
        original_countdown = self.engine._countdown_ms
        self.engine.handle_event(SwitchingEvent.SKIP_NEXT)
        
        # Countdown should be reset to a new interval
        assert self.engine._countdown_ms > 0
    
    def test_extend_time_adds_to_countdown(self):
        """EXTEND_TIME adds duration to countdown."""
        self.engine.handle_event(SwitchingEvent.START)
        
        original_countdown = self.engine._countdown_ms
        self.engine.handle_event(SwitchingEvent.EXTEND_TIME, duration_ms=5000)
        
        assert self.engine._countdown_ms == original_countdown + 5000
    
    def test_disconnect_reconnect_transitions(self):
        """DISCONNECT/RECONNECT state transitions."""
        self.engine.handle_event(SwitchingEvent.START)
        assert self.engine._state == SwitchingState.RUNNING
        
        self.engine.handle_event(SwitchingEvent.DISCONNECT)
        assert self.engine._state == SwitchingState.RECONNECTING
        
        self.engine.handle_event(SwitchingEvent.RECONNECT)
        assert self.engine._state == SwitchingState.RUNNING


class TestStateSnapshots:
    """Test state query interface."""
    
    def setup_method(self):
        """Set up test engine."""
        self.config = SwitchingConfig()
        self.engine = SwitchingEngine(self.config, PureRandomMode())
        
        for i in range(1, 5):
            self.engine._input_states[i] = InputState(
                input_index=i,
                has_signal=True,
                operator_enabled=True,
            )
    
    def test_get_state_returns_snapshot(self):
        """get_state returns current state snapshot."""
        self.engine.handle_event(SwitchingEvent.START)
        
        snapshot = self.engine.get_state()
        
        assert snapshot.state == SwitchingState.RUNNING
        assert snapshot.current_input == self.engine.current_input
        assert len(snapshot.eligible_inputs) > 0
    
    def test_callbacks_registered(self):
        """Callbacks can be registered."""
        switch_called = []
        state_called = []
        
        self.engine.register_switch_callback(
            lambda old, new: switch_called.append((old, new))
        )
        self.engine.register_state_callback(
            lambda state: state_called.append(state)
        )
        
        self.engine.handle_event(SwitchingEvent.START)
        
        # Should have called state callback
        assert len(state_called) > 0
