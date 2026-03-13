Orchestration Service Documentation

## Overview

The ApplicationOrchestrator is the application brain that coordinates all subsystems:
- ATEM adapter (device connection and state)
- Switching engine (automated camera switching)
- Persistence layer (config, stats, events)
- Runtime state management
- Dashboard state publication
- Error handling and recovery

It maintains a single RuntimeState that serves as the source of truth for the entire application.

## Architecture

### Three-Layer Design

1. **RuntimeState** - Single source of truth
   - ATEM device state (connection, inputs, signals)
   - Switching engine state (IDLE, READY, RUNNING, etc.)
   - Camera states (per-input enable/disable, signal, cooldown)
   - Session statistics
   - Configuration

2. **ApplicationOrchestrator** - Coordinator
   - Initializes all subsystems
   - Manages lifecycle (boot, running, shutdown)
   - Handles cross-subsystem coordination
   - Manages background tasks
   - Publishes state changes

3. **Subsystems** - Independent components
   - ATEMManager - Device communication
   - SwitchingEngine - Domain logic
   - StorageManager - Persistence
   - Each has isolated responsibility

### Key Responsibilities

#### Initialization (5 steps)
1. Load persisted configuration
2. Connect to ATEM device
3. Initialize switching engine
4. Sync device state
5. Start background monitoring

#### Runtime Management
- Monitor device state changes
- Execute engine switch commands
- Record statistics and events
- Handle reconnection
- Manage error states

#### Edge Case Handling
- Zero eligible inputs → retry with 5s delay
- One eligible input → switch automatically
- Disconnect during countdown → stop switching
- Signal loss → immediate fallback
- Operator manual changes → detect and track
- Lock/hold transitions → respect operator overrides

## State Management

### RuntimeState Structure

```python
RuntimeState:
  - atem_manager: ATEMManager
  - atem_status: ATEMStatus
  - switcher_state: SwitcherState
  - switching_engine: SwitchingEngine
  - engine_state: SwitchingState
  - operation_mode: OperationMode (MANUAL, AUTO, FAILSAFE)
  - camera_states: Dict[int, CameraState]
  - session_stats: SwitchingSessionStats
  - is_initialized: bool
  - last_error: Optional[str]
```

### Operation Modes

- **MANUAL** - User controls switches, no automation
- **AUTO** - Automatic switching enabled
- **FAILSAFE** - Restricted mode after errors, manual only

### Camera States

Per-input state tracking:
- enabled: Operator enable/disable
- has_signal: Current signal presence
- is_current_program/preview: Current usage
- is_locked: Temporarily locked by engine
- cooldown_expires_at: When re-selection allowed
- Statistics: switch count, program time, average hold

## API

### Initialization & Shutdown

```python
await orchestrator.initialize()  # Boot application
await orchestrator.shutdown()    # Graceful shutdown
```

### Switching Control

```python
# Manual switching
await orchestrator.switch_to_input(3, reason="manual")

# Engine control
await orchestrator.start_auto_switching()
await orchestrator.stop_auto_switching()

# Engine commands
await orchestrator.skip_current_camera()
await orchestrator.hold_current_camera(hold=True)
```

### State Access

```python
# Get complete dashboard state
dashboard = await orchestrator.get_dashboard_state()

# Register callback for state changes
def on_state_change(dashboard_state: DashboardState):
    print(f"State changed: {dashboard_state}")

orchestrator.register_state_callback(on_state_change)
```

## Background Tasks

### Monitoring Loop (500ms)
- Polls ATEM device status
- Updates input signals
- Syncs streaming/recording status

### Engine Tick Loop (100ms)
- Reads current program input
- Evaluates eligible inputs
- Executes engine state machine
- Applies switch commands

### Stats Sync Loop (30s)
- Persists session statistics
- Updates cumulative stats
- Backs up to storage

## Error Handling

### Connection Failures

```
MANUAL → (connection lost) → FAILSAFE
  ↓ (reconnect)
  → MANUAL / AUTO (based on previous state)
```

### Recovery Strategy

1. Log error with context
2. Set operation_mode to FAILSAFE
3. Emit state change (UI updates)
4. Attempt reconnection (automatic)
5. Resume normal operation on success

### Safe Fallbacks

- If all inputs lose signal → stop switching
- If device disconnects → use safe camera
- If engine errors → manual mode only
- If switch fails → log and continue

## Event Recording

All significant events are recorded:

```python
# Switch events
{
  event_type: "switch",
  from_input: 1,
  to_input: 3,
  reason: "auto_switch",
  is_success: true,
  hold_duration: 30.5
}

# Manual overrides
{
  event_type: "override",
  to_input: 2,
  reason: "operator_manual"
}

# Device events
{
  event_type: "signal_loss",
  input_index: 4,
  is_success: true
}
```

## Session Management

### Starting Session

```python
await orchestrator.start_auto_switching()
```

Creates:
- SwitchingSessionStats (start time, counters)
- Event log entry
- Background monitoring

### During Session

Tracks:
- Total switches
- Average hold time
- Last switch details
- Per-camera statistics

### Ending Session

```python
await orchestrator.stop_auto_switching()
```

Persists:
- Complete session summary
- Final statistics
- Event log

## Testing

Use mock implementations for testing:

```python
from unittest.mock import AsyncMock

# Mock ATEM manager
orch.atem_manager = AsyncMock()
orch.atem_manager.connect = AsyncMock()
orch.atem_manager.get_status = AsyncMock(return_value=ATEMStatus(...))

# Mock storage
mock_storage = AsyncMock(spec=StorageManager)

# Mock switching engine
orch.switching_engine = MagicMock()
orch.switching_engine.handle_event = MagicMock()
```

## Integration Example

```python
# Create orchestrator
orchestrator = ApplicationOrchestrator(config, storage)

# Initialize
await orchestrator.initialize()

# Register state callbacks for UI
orchestrator.register_state_callback(websocket.send_json)

# Start auto-switching
await orchestrator.start_auto_switching()

# Handle user input
await orchestrator.switch_to_input(3)
await orchestrator.skip_current_camera()

# Get state for dashboard
state = await orchestrator.get_dashboard_state()

# Graceful shutdown
await orchestrator.shutdown()
```

## Performance Considerations

- State is thread-safe via asyncio.Lock
- Background tasks run independently
- Callbacks are non-blocking
- Device polling is efficient (signals only)
- Storage operations are async
- No blocking I/O in event handlers
