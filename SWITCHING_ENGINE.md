# Switching Engine Documentation

## Overview

The switching engine is the core domain module for automated camera switching. It implements an explicit state machine with 7 states, 16+ events, multiple switching modes, and comprehensive safety rules.

**Key Design Principles:**
- Pure domain logic separated from infrastructure
- Explicit state machine (not hidden timers)
- Deterministic where possible
- Strong typing throughout
- No fragile hidden mutations
- Comprehensive safety rules

## Architecture

### State Machine

```
┌─────────┐
│  IDLE   │ (Initial, waiting for START)
└────┬────┘
     │ START
     ▼
┌─────────┐
│ READY   │ (Configured, initializing)
└────┬────┘
     │
     ▼
┌─────────────┐
│   RUNNING   │◄───► PAUSED (HOLD_CURRENT)
│  (Actively  │
│ switching)  │
└──┬──────┬───┘
   │      │ SIGNAL_LOST (on current)
   │      │ INPUT_DISABLED (on current)
   │      ▼
   │   ┌────────┐
   │   │ LOCKED │ (Lock expires automatically)
   │   └────────┘
   │
   ├──► RECONNECTING (DISCONNECT)
   │    ▲         │
   │    └─────────┘ RECONNECT
   │
   ├──► ERROR
   │
   └──► IDLE (STOP)
```

### Core States

- **IDLE**: Waiting for START. No switching occurs.
- **READY**: Configured and ready, initializing inputs.
- **RUNNING**: Actively switching cameras on schedule.
- **PAUSED**: Temporarily paused via HOLD_CURRENT. Current input held.
- **LOCKED**: Current input locked for specified duration. No switching.
- **RECONNECTING**: Device disconnected, waiting for reconnect.
- **ERROR**: Fatal error occurred. Manual recovery needed.

### Events

```
Start/Stop Control:
  START               - Begin switching
  STOP                - Stop and return to IDLE
  TICK                - Time increment (typically 1 second)

Manual Override:
  SKIP_CURRENT        - Switch immediately to next eligible input
  SKIP_NEXT           - Extend current, re-randomize next interval
  EXTEND_TIME         - Add duration to current interval (e.g., +30s, +1m)
  HOLD_CURRENT        - Pause/resume switching (toggle)
  LOCK_CURRENT        - Lock current input for duration
  RELEASE_LOCK        - Manually release lock

Input/Device Events:
  SIGNAL_LOST         - Input lost signal
  SIGNAL_RESTORED     - Input signal restored
  INPUT_ENABLED       - Operator enabled input
  INPUT_DISABLED      - Operator disabled input
  MANUAL_SWITCH_DETECTED - Operator switched on device
  DISCONNECT          - Device disconnected
  RECONNECT           - Device reconnected
```

## Usage

### Basic Usage

```python
from atem_director.engine.switching import (
    SwitchingEngine,
    SwitchingConfig,
    SwitchingEvent,
    BalancedRandomMode,
)

# Configure engine
config = SwitchingConfig(
    interval_pool=[30000, 60000, 90000, 120000, 150000],  # ms
    avoid_repeat_same_input=True,
    same_input_cooldown_ms=2000,
)

# Create engine with switch mode
engine = SwitchingEngine(config, BalancedRandomMode())

# Initialize input states (typically from ATEM device)
from atem_director.engine.switching import InputState
for i in range(1, 9):
    engine._input_states[i] = InputState(
        input_index=i,
        has_signal=True,
        operator_enabled=True,
    )

# Register callbacks
engine.register_switch_callback(
    lambda old, new: print(f"Switched from {old} to {new}")
)

# Start switching
engine.handle_event(SwitchingEvent.START)

# Simulate time passing (call once per second)
while True:
    engine.handle_event(SwitchingEvent.TICK)
    await asyncio.sleep(1.0)
```

### Switch Modes

#### PureRandomMode
Randomly selects from all eligible inputs. No weighting or avoiding repeats.

```python
from atem_director.engine.switching import PureRandomMode
engine = SwitchingEngine(config, PureRandomMode())
```

#### BalancedRandomMode (Recommended)
Randomly selects, avoiding current input when alternatives exist.

```python
from atem_director.engine.switching import BalancedRandomMode
engine = SwitchingEngine(config, BalancedRandomMode())
```

#### WeightedRandomMode
Weights selection by input usage. Less-used inputs selected more frequently.

```python
from atem_director.engine.switching import WeightedRandomMode
engine = SwitchingEngine(config, WeightedRandomMode(weight_by_frequency=True))
```

#### RoundRobinRandomMode
Cycles through inputs in order with random intervals.

```python
from atem_director.engine.switching import RoundRobinRandomMode
engine = SwitchingEngine(config, RoundRobinRandomMode())
```

### Handling Events

```python
# Manual skip to next input immediately
engine.handle_event(SwitchingEvent.SKIP_CURRENT)

# Extend current interval by 30 seconds
engine.handle_event(SwitchingEvent.EXTEND_TIME, duration_ms=30000)

# Lock current input for 5 seconds
engine.handle_event(SwitchingEvent.LOCK_CURRENT, duration_ms=5000)

# Pause/resume switching
engine.handle_event(SwitchingEvent.HOLD_CURRENT)

# Handle input signal loss
engine.handle_event(SwitchingEvent.SIGNAL_LOST, input_index=1)

# Handle operator disabling input
engine.handle_event(SwitchingEvent.INPUT_DISABLED, input_index=2)

# Handle device reconnect
engine.handle_event(SwitchingEvent.DISCONNECT)
engine.handle_event(SwitchingEvent.RECONNECT)
```

### Querying State

```python
# Get full state snapshot
state = engine.get_state()
print(f"Current state: {state.state}")
print(f"Current input: {state.current_input}")
print(f"Next input: {state.next_input}")
print(f"Time to switch: {state.time_until_switch_ms}ms")
print(f"Eligible inputs: {state.eligible_inputs}")
print(f"Is locked: {state.is_locked}")

# Quick queries
print(f"Currently switching: {engine.is_running}")
print(f"Current input: {engine.current_input}")
print(f"Eligible inputs: {engine.eligible_inputs}")
print(f"Total switches: {engine.total_switches}")
```

## Safety Rules

### Mandatory Safety Checks

1. **Signal Presence**
   - Never switch to input without signal
   - Inputs without signal marked as non-eligible
   - Signal loss on current input triggers immediate switch

2. **Operator Control**
   - Never switch to operator-disabled input
   - Operator can disable/enable inputs dynamically
   - Disabling current input triggers immediate switch (unless locked)

3. **Repeat Prevention**
   - By default, avoids switching to same input twice in a row
   - Configurable: `avoid_repeat_same_input`
   - Bypassed when it's the only eligible input
   - Optional cooldown before re-selecting same input

4. **Manual Override Respect**
   - Detects when operator switches on device
   - Temporarily disables auto-switching
   - Duration: `manual_override_duration_ms`

5. **Eligibility Re-evaluation**
   - Re-evaluates eligibility at actual switch time
   - Prevents switching to inputs that became ineligible
   - Safe handling of race conditions

6. **Zero-Eligible Fallback**
   - If no inputs eligible, waits and retries
   - Retry interval: 5 seconds
   - Eventually triggers ERROR state if continues

### Configuration Options

```python
config = SwitchingConfig(
    # Interval configuration
    interval_pool=[30000, 60000, 90000, 120000, 150000],
    enabled_intervals={30000, 60000, 90000},  # Can selectively enable
    
    # Safety settings
    avoid_repeat_same_input=True,
    same_input_cooldown_ms=2000,
    enable_signal_loss_protection=True,
    
    # Manual override handling
    respect_manual_override=True,
    manual_override_duration_ms=30000,
)
```

## Integration Points

### With ATEM Adapter

```python
from atem_director.atem_layer.manager import ATEMManager
from atem_director.engine.switching import SwitchingEngine

atem_manager = ATEMManager(config)
engine = SwitchingEngine(config)

# Subscribe to ATEM status changes
def on_input_signals_changed(signals):
    # signals: Dict[int, bool]
    engine.set_input_signals(signals)

# Subscribe to switching engine output
engine.register_switch_callback(
    lambda old, new: atem_manager.set_program_input(new)
)
```

### With REST API

```python
@app.post("/api/v1/switcher/skip")
async def skip_current_input():
    """Skip to next input immediately."""
    engine.handle_event(SwitchingEvent.SKIP_CURRENT)
    return {"status": "switched"}

@app.post("/api/v1/switcher/extend")
async def extend_current_input(duration_ms: int):
    """Extend current input by duration."""
    engine.handle_event(
        SwitchingEvent.EXTEND_TIME,
        duration_ms=duration_ms,
    )
    return {"status": "extended"}

@app.get("/api/v1/switcher/state")
async def get_switcher_state():
    """Get switching engine state."""
    state = engine.get_state()
    return state.model_dump()
```

## Testing

### Unit Tests

Run tests:
```bash
pytest tests/test_switching_engine.py -v
```

Test coverage:
- State transitions (7 states × transitions)
- All events (16 events)
- Switch modes (4 modes)
- Safety rules (signal, operator, repeat, cooldown)
- Edge cases (no eligible, single eligible, locked, paused)
- Callbacks and state queries

### Test-Driven Switching

Use mock switching for testing without hardware:

```python
from atem_director.engine.switching import (
    SwitchingEngine,
    SwitchingConfig,
    BalancedRandomMode,
    InputState,
)

# Create test engine
config = SwitchingConfig()
engine = SwitchingEngine(config, BalancedRandomMode())

# Set up test inputs
for i in range(1, 5):
    engine._input_states[i] = InputState(
        input_index=i,
        has_signal=True,
        operator_enabled=True,
    )

# Test behavior
engine.handle_event(SwitchingEvent.START)
assert engine.is_running

# No ATEM hardware needed!
```

## Performance

- **Memory**: ~5KB per switching engine instance
- **CPU**: <1% during switching operations
- **Latency**: <1ms for event handling
- **Deterministic**: All operations O(1) or O(n) where n=number of inputs (≤8)

## Logging

Engine logs state transitions and events at appropriate levels:

```
DEBUG  - Detailed event handling
INFO   - State changes, switches performed
WARNING - Safety rule violations, signal loss
ERROR - Fatal errors
```

Example logs:
```
INFO: State transition from_state=idle to_state=running
INFO: Performing switch from_input=1 to_input=3 total_switches=42
WARNING: Signal lost input_index=2
INFO: Input disabled input_index=4
```

## Common Patterns

### Automatic Daily Reset

```python
# Reset switching pattern daily at midnight
async def daily_reset():
    while True:
        tomorrow = datetime.now().replace(
            hour=0, minute=0, second=0
        ) + timedelta(days=1)
        sleep_seconds = (tomorrow - datetime.now()).total_seconds()
        await asyncio.sleep(sleep_seconds)
        
        engine.handle_event(SwitchingEvent.STOP)
        engine.handle_event(SwitchingEvent.START)
```

### Scheduled Maintenance Mode

```python
# Disable switching during maintenance
async def maintenance_mode(duration_seconds):
    engine.handle_event(SwitchingEvent.HOLD_CURRENT)
    await asyncio.sleep(duration_seconds)
    engine.handle_event(SwitchingEvent.HOLD_CURRENT)  # Resume
```

### Emergency Fallback

```python
# Lock to safe input during emergency
def emergency_fallback(safe_input_index):
    engine._current_input = safe_input_index
    engine.handle_event(
        SwitchingEvent.LOCK_CURRENT,
        duration_ms=3600000,  # 1 hour
    )
```

## Troubleshooting

### Engine stops switching
- Check all inputs are marked has_signal=True
- Verify at least one input has operator_enabled=True
- Check logs for SIGNAL_LOST or INPUT_DISABLED events

### Same input selected repeatedly
- Check interval_pool is configured correctly
- Verify enabled_intervals contains enabled intervals
- Inspect switch mode selection logic

### Operator override not respected
- Verify respect_manual_override=True in config
- Check manual_override_duration_ms is appropriate
- Monitor MANUAL_SWITCH_DETECTED events

### State machine stuck
- Check for unhandled events
- Verify TICK events are sent periodically
- Look for ERROR state (may need manual recovery)
