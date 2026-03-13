"""ATEM Integration Boundary Documentation.

This module implements a production-ready ATEM adapter/service layer that
isolates low-level ATEM communication from the rest of the system.

## Architecture Overview

The ATEM integration is built with clear separation of concerns:

1. **ATEMProtocolAdapter (ABC)**: Abstract interface for ATEM protocol communication
   - Defines contract for ATEM operations
   - Allows swapping implementations (real vs. mock)
   - Enables testing without hardware

2. **PyATEMAdapter**: Real implementation using pyatem library
   - Handles actual device communication
   - Implements fallback behaviors
   - Provides error recovery

3. **ATEMManager**: High-level manager
   - Connection lifecycle management
   - State tracking and callbacks
   - Input monitoring
   - Capability-aware operations

## Key Features

### Connection Management
- Configurable IP/port
- Connect/disconnect/reconnect operations
- Automatic reconnection with exponential backoff
- Connection state tracking (disconnected, connecting, connected, reconnecting, error)

### State Monitoring
- Program/preview input tracking
- Input signal state for inputs 1-8
- Live stream and recording status
- Transition mode and duration

### Transition Control
- Cut transitions (immediate)
- Mix transitions with configurable duration
- Panic cut support (best-effort)
- Capability-aware operation

### Input Signal Monitoring
- Real-time signal state for all inputs
- Contextual signal labeling (none, program, preview)
- Background monitoring loop

### Error Handling & Fallbacks
- Connection failure recovery
- Graceful degradation when capabilities unavailable
- Safe fallback to cut mode when mix unavailable
- Non-blocking panic cut operation

## Connection State Machine

```
    DISCONNECTED
        ↓ (connect called)
    CONNECTING
        ↓ (handshake)
    CONNECTED → RECONNECTING (reconnect called)
        ↓                  ↓
    ERROR              CONNECTING
        ↓                  ↓
    (retry)            CONNECTED
```

## Usage Examples

### Basic Connection

```python
from atem_director.config import ATEMConfig
from atem_director.atem_layer.manager import ATEMManager

config = ATEMConfig(host="192.168.1.100", port=21124)
manager = ATEMManager(config)

# Connect
await manager.connect()

# Check status
status = await manager.get_status()
print(f"Connected: {manager.is_connected}")

# Disconnect
await manager.disconnect()
```

### Switching Operations

```python
# Get current state
state = await manager.get_switcher_state()
print(f"Program: {state.program_input}, Preview: {state.preview_input}")

# Set program input
await manager.set_program_input(2)

# Set preview input
await manager.set_preview_input(3)

# Configure transition
await manager.set_transition_mode(TransitionMode.MIX)
await manager.set_mix_duration(500)

# Perform cut (panic)
await manager.panic_cut()
```

### Connection Callbacks

```python
def on_connection_change(state):
    print(f"Connection state: {state}")

manager.register_connection_callback(on_connection_change)

def on_state_change(switcher_state):
    print(f"Program: {switcher_state.program_input}")

manager.register_state_callback(on_state_change)
```

### Testing with Mock

```python
from atem_director.atem_layer.manager import MockATEMAdapter

mock_adapter = MockATEMAdapter()
manager = ATEMManager(config, adapter=mock_adapter)

# Works same as real adapter but without hardware
await manager.connect()
```

## Limitations & Design Decisions

### pyatem Integration
- Uses pyatem library for device communication
- Handles TCP connection to device port 21124
- Implements safe handshake timeout (default 5s)
- Graceful error handling for connection failures

### Input Monitoring
- Background monitoring loop runs every 500ms
- Checks inputs 1-8 for signal state
- Updates signal_state based on current program/preview inputs
- Continues running as long as connected

### Transition Support
- Cut transitions: Immediate with no delay
- Mix transitions: Configurable 1-5000ms duration
- Capability checking: Falls back to cut if mix unavailable
- Duration validation: Checks against device capabilities

### Reconnection Behavior
- Exponential backoff: delay * 2, capped at 30s
- Configurable attempt count (default: 5)
- Metrics tracking: Success/failure counts, last error
- Safe state cleanup on disconnect

### Fallback Behaviors
When ATEM is unavailable:
- Connection: Returns DISCONNECTED state
- Input queries: Return safe defaults (empty signals)
- Switching operations: Raise RuntimeError
- Panic cut: Logs warning, continues without raising

## Signal State Examples

When input 1 has signal and is program input:
```python
signal = state.input_signals[1]
# signal.input_index = 1
# signal.has_signal = True
# signal.signal_state = InputSignalState.PROGRAM
```

When input 2 has no signal:
```python
signal = state.input_signals[2]
# signal.input_index = 2
# signal.has_signal = False
# signal.signal_state = InputSignalState.NONE
```

## Capability Detection

Device capabilities are tracked and used for:
- Mix transition support: Falls back to cut if unavailable
- Duration validation: Ensures requested duration in range
- Feature availability: Used by orchestration layer

Example:
```python
caps = status.capabilities
print(f"Supports mix: {caps.supports_mix_transition}")
print(f"Max duration: {caps.max_mix_duration_ms}ms")
```

## Error Handling Strategy

1. **Connection Errors**: Retry with exponential backoff
2. **Operation Errors**: Log and raise for upper layers
3. **State Errors**: Use safe defaults (empty, false, 0)
4. **Callback Errors**: Log but don't interrupt other callbacks
5. **Panic Cut**: Best-effort, never raises

## Testing Strategy

The adapter is fully mockable and testable:

1. **Unit Tests**: Test state machines, transitions, monitoring
2. **Mock Adapter**: Simulates device behavior without hardware
3. **Error Scenarios**: Connection failures, invalid inputs
4. **Callback Testing**: Verify callbacks are invoked
5. **Integration Tests**: Real pyatem library (when available)

## Performance Considerations

- State queries: Non-blocking, return immediately
- Monitoring: Background task, doesn't block operations
- Connection: Timeout-protected, configurable
- Callbacks: Best-effort, errors logged not raised
- Input signals: Updated every 500ms (configurable)

## Security Considerations

- No authentication built-in (ATEM devices typically on local network)
- TCP connection to hardcoded port 21124
- No encryption (standard for ATEM protocol)
- Assume trusted network environment

## Future Enhancements

1. Multiple device support
2. Device capability auto-detection
3. State persistence/recovery
4. Event streaming
5. Rate limiting
6. Metrics exposure (Prometheus)
7. WebSocket support
8. Device firmware updates
"""
