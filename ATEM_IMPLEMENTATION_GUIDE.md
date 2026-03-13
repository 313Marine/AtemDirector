# ATEM Integration Boundary Implementation Guide

## Overview

This document explains the production-ready ATEM adapter/service layer implementation and the design decisions made.

## Architecture

### Layer 1: Protocol Adapter (ATEMProtocolAdapter)
**Responsibility**: Abstract interface for low-level ATEM communication

```
┌─────────────────────────┐
│ ATEMProtocolAdapter     │
│ (Abstract Base Class)   │
├─────────────────────────┤
│ + connect()             │
│ + disconnect()          │
│ + get_device_info()     │
│ + get_input_signals()   │
│ + set_program_input()   │
│ + set_preview_input()   │
│ + set_transition_mode() │
│ + set_mix_duration()    │
│ + perform_cut()         │
│ + get_streaming_status()│
│ + get_recording_status()│
└─────────────────────────┘
```

**Why ABC?**
- Defines contract clearly
- Enables mock implementations for testing
- Makes dependency injection explicit
- Supports multiple implementations (real, mock, simulator)

### Layer 2: Protocol Implementation (PyATEMAdapter)
**Responsibility**: Real device communication using pyatem library

**Key Features:**
- TCP connection to device on port 21124
- Async handshake with timeout protection
- Error recovery on connection failure
- Safe defaults when queries fail
- Graceful handling of optional capabilities

**Error Handling:**
- ImportError: Logs and raises ConnectionError
- TimeoutError: Cleans up connection, raises
- Generic Exception: Logs, raises ConnectionError
- Query Failures: Returns safe defaults

**Fallback Behavior:**
- Missing device info: Empty dict
- Signal queries: All false (no signal)
- Program/preview: Return safe defaults (0, 1)
- Streaming/recording: Return false

### Layer 3: Manager (ATEMManager)
**Responsibility**: High-level connection and state management

**Key Components:**
1. Connection State Machine
   - DISCONNECTED: Initial state, no device
   - CONNECTING: Attempting to establish connection
   - CONNECTED: Active connection, ready for operations
   - RECONNECTING: Lost connection, attempting recovery
   - ERROR: Connection failed permanently

2. State Tracking
   - ATEMStatus: Device capabilities, model, firmware
   - SwitcherState: Current program/preview, transition settings
   - InputSourceSignal: Per-input signal state

3. Background Monitoring
   - Continuous loop while connected
   - Updates input signals every 500ms
   - Tracks streaming/recording status
   - Non-blocking, independent task

4. Callback System
   - Connection state changes: Notify subscribers
   - Switcher state changes: Notify subscribers
   - Async callback support
   - Error handling: Log but don't interrupt

## Connection State Machine

```
START
  │
  ├─→ connect() → CONNECTING
  │               │
  │               ├─→ Success → CONNECTED
  │               │             │
  │               │             ├─→ disconnect() → DISCONNECTED
  │               │             │
  │               │             ├─→ reconnect() → RECONNECTING
  │               │             │                   │
  │               │             │                   └─→ CONNECTING
  │               │             │
  │               │             └─→ Connection Lost → ERROR
  │               │
  │               └─→ Timeout/Failure → ERROR (retry)
  │
  └─→ Metrics Tracked:
      - total_attempts
      - successful_connections
      - failed_connections
      - last_attempt_time
      - last_successful_time
      - error_count_since_last_success
      - last_error
```

## Key Implementation Details

### 1. Connection Retry Logic

```python
async def connect(self) -> None:
    """Exponential backoff retry with configurable attempts."""
    attempt = 0
    backoff_delay = self.config.reconnect_delay  # Start at configured delay
    
    while attempt < self.config.reconnect_attempts:
        try:
            # Attempt connection with timeout
            await self.adapter.connect(...)
            # Success
            return
        except (ConnectionError, TimeoutError) as e:
            # Log and retry
            attempt += 1
            if attempt < max_attempts:
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, 30.0)  # Cap at 30s
```

**Why Exponential Backoff?**
- Avoids hammering device during temporary outages
- Scales gracefully with failure time
- Configurable max delay prevents excessive waits
- Metrics track attempt history

### 2. Input Signal Monitoring

```python
async def _monitoring_loop(self) -> None:
    """Background monitoring of device state."""
    while self.is_connected:
        # Query input signals
        signals = await self.adapter.get_input_signals()
        
        # Update state with signal info
        for input_idx, has_signal in signals.items():
            # Determine signal state based on program/preview
            signal_state = InputSignalState.PROGRAM if ...
            
            # Store in state
            self._switcher_state.input_signals[input_idx] = (
                InputSourceSignal(...)
            )
        
        # Update streaming/recording
        self._switcher_state.live_stream_active = (
            await self.adapter.get_streaming_status()
        )
        
        # Sleep before next check
        await asyncio.sleep(0.5)
```

**Design Decisions:**
- Background task: Doesn't block operations
- 500ms interval: Reasonable latency vs. load
- Non-blocking updates: Uses state lock
- Continues on errors: Logs warning, retries

### 3. Capability-Aware Operations

```python
async def set_transition_mode(self, mode: TransitionMode) -> None:
    """Set transition with fallback to cut if mix unavailable."""
    if mode == TransitionMode.MIX:
        if not self._status.capabilities.supports_mix_transition:
            logger.warning("Device does not support mix, using cut")
            mode = TransitionMode.CUT  # Fallback
    
    await self.adapter.set_transition_mode(mode)
```

**Benefits:**
- Graceful degradation
- No operation failures due to capabilities
- Transparent fallback to user
- Logged for debugging

### 4. Safe Lock Usage

```python
async def get_status(self) -> ATEMStatus:
    """Thread-safe status retrieval."""
    async with self._state_lock:
        self._status.state = self._state
        # ... update other fields
        return self._status.model_copy()  # Return copy
```

**Design Decisions:**
- Lock held briefly
- Return copy, not reference
- Prevents concurrent modification
- Async lock respects event loop

### 5. Panic Cut Implementation

```python
async def panic_cut(self) -> None:
    """Best-effort panic cut, never raises."""
    try:
        logger.warning("Executing panic cut")
        if self.is_connected:
            await self.adapter.perform_cut()
        else:
            logger.warning("Panic cut called but disconnected")
    except Exception as e:
        logger.error("Panic cut failed", error=str(e))
        # Don't raise - best effort operation
```

**Why No Exception?**
- Panic cut is emergency operation
- Caller shouldn't need try/except
- Logging sufficient for diagnostics
- Logging ensures visibility

## Testing Strategy

### Unit Tests (test_atem_adapter.py)

1. **Connection States**
   - Initial state is DISCONNECTED
   - Successfully connect → CONNECTED
   - Disconnect → DISCONNECTED
   - Connection failure → ERROR

2. **State Callbacks**
   - Callbacks invoked on state change
   - Multiple callbacks work
   - Callback errors logged, not raised

3. **Switcher Control**
   - Set program/preview when connected
   - Raises RuntimeError when disconnected
   - State updated correctly
   - Transitions work as configured

4. **Input Monitoring**
   - Input signals populated while connected
   - Signal state reflects program/preview
   - Monitoring stops on disconnect

5. **Error Handling**
   - Invalid input ranges raise ValueError
   - Invalid mix durations raise ValueError
   - Reconnect works
   - Panic cut doesn't raise

### Mock Adapter

```python
class MockATEMAdapter(ATEMProtocolAdapter):
    """Simulates ATEM device for testing."""
    
    def __init__(self):
        self.connected = False
        self.program_input = 1
        self.preview_input = 2
        # ... other state
```

**Benefits:**
- No hardware required
- Fast test execution
- Deterministic behavior
- Error scenario simulation

## Limitations & Future Improvements

### Current Limitations

1. **Single Device**: Only one ATEM device supported
2. **No Authentication**: Assumes trusted network
3. **No Persistence**: State not persisted across restarts
4. **Manual Capability Config**: Must configure capabilities manually

### Future Enhancements

1. **Multiple Devices**
   ```python
   manager1 = ATEMManager(config1)
   manager2 = ATEMManager(config2)
   orchestrator = MultiDeviceOrchestrator([manager1, manager2])
   ```

2. **Auto Device Detection**
   ```python
   # Query device for supported capabilities
   caps = await adapter.get_device_capabilities()
   ```

3. **State Persistence**
   ```python
   # Save/restore state on restart
   await manager.save_state("state.json")
   await manager.load_state("state.json")
   ```

4. **WebSocket Support**
   ```python
   # Real-time updates to clients
   ws.send_json(state)
   ```

5. **Prometheus Metrics**
   ```python
   CONNECTION_ATTEMPTS.inc()
   CONNECTION_TIME.observe(duration)
   ```

## Integration with REST API

The ATEM manager integrates with REST API endpoints:

```python
# src/atem_director/api/switcher.py

@router.get("/status")
async def get_status(manager: ATEMManager = Depends(get_manager)):
    """Get ATEM device status."""
    return await manager.get_status()

@router.post("/program/{input_index}")
async def set_program(input_index: int, manager = Depends()):
    """Set program input."""
    await manager.set_program_input(input_index)
    return await manager.get_switcher_state()

@router.post("/cut")
async def cut(manager = Depends()):
    """Perform panic cut."""
    await manager.panic_cut()
    return {"status": "cut_executed"}
```

## Configuration

```python
# .env

ATEM_HOST=192.168.1.100
ATEM_PORT=21124
ATEM_CONNECTION_TIMEOUT=5.0
ATEM_RECONNECT_ATTEMPTS=5
ATEM_RECONNECT_DELAY=1.0
```

Loaded by `ATEMConfig`:

```python
@dataclass
class ATEMConfig:
    host: str = "192.168.1.100"
    port: int = 21124
    connection_timeout: float = 5.0
    reconnect_attempts: int = 5
    reconnect_delay: float = 1.0
```

## Monitoring & Debugging

### Logging

All operations logged with structlog:

```
{"event": "Connecting to ATEM device", "host": "192.168.1.100", ...}
{"event": "Connection state changed", "from_state": "disconnected", "to_state": "connected"}
{"event": "Set program input", "input_index": 2}
```

### Metrics

Access via `manager.metrics`:

```python
metrics = manager.metrics
print(f"Total attempts: {metrics.total_attempts}")
print(f"Successful: {metrics.successful_connections}")
print(f"Last error: {metrics.last_error}")
```

### Status API

```bash
curl http://localhost:8000/api/v1/switcher/status
{
  "state": "connected",
  "model": "ATEM Mini Extreme ISO 12G",
  "firmware_version": "1.0.0",
  "inputs_count": 4,
  "last_error": null
}
```

## Conclusion

This ATEM integration provides a production-ready abstraction layer that:

✅ Isolates device communication from application logic
✅ Provides robust connection management with recovery
✅ Handles state safely with locks and callbacks
✅ Implements graceful fallbacks and degradation
✅ Supports comprehensive testing with mocks
✅ Delivers strong typing and logging
✅ Scales to REST API and higher-level orchestration
