"""System Architecture and Integration Guide

## Complete System Architecture

### Layer 1: Infrastructure (Bottom)
- ATEM Adapter: TCP connection to device, protocol handling
- Database: SQLite/PostgreSQL for persistence
- Logging: structlog for production logging

### Layer 2: Domain Logic
- ATEM Layer: Device state models and connection management
- Switching Engine: State machine, switching algorithms, business rules
- Persistence: Repositories for data access patterns

### Layer 3: Orchestration (Middle)
- Runtime State: Single source of truth
- Application Orchestrator: Coordinates all subsystems

### Layer 4: API (Top)
- REST Routes: Thin handlers delegating to orchestrator
- WebSocket: Dashboard state publication
- Authentication: User management

## Data Flow

### Initialization Sequence

```
Application Start
    ↓
ApplicationOrchestrator.initialize()
    ├─ Load config from storage
    ├─ ATEMManager.connect() → device discovered
    ├─ SwitchingEngine.__init__() → ready state
    ├─ Sync device state into RuntimeState
    ├─ Initialize per-camera states
    ├─ Register callbacks
    └─ Start background tasks

Background Tasks Start
    ├─ Monitoring Loop (500ms): poll device → update RuntimeState
    ├─ Stats Sync Loop (30s): persist statistics
    └─ Engine Tick Loop (on auto-switch): drive state machine
```

### Switch Execution (Auto)

```
Engine Tick Loop (100ms)
    ├─ Read current program input
    ├─ Evaluate eligible inputs (signal presence, enabled, not locked)
    ├─ engine.tick(current_input, eligible_inputs)
    ├─ Get next action from engine
    └─ If action.input != current:
        ├─ orchestrator.switch_to_input()
        │   ├─ ATEMManager.set_program_input()
        │   ├─ Update RuntimeState.switcher_state
        │   ├─ Update RuntimeState.camera_states
        │   ├─ storage.record_event()
        │   ├─ Publish state change
        │   └─ Callback: websocket.send_json(state)
```

### Switch Execution (Manual)

```
REST API: POST /api/v1/switcher/program/{input}
    ├─ Validate input
    ├─ orchestrator.switch_to_input(input)
    │   ├─ ATEMManager.set_program_input()
    │   ├─ Update RuntimeState
    │   ├─ storage.record_event()
    │   └─ Publish state change
    └─ Return updated dashboard state
```

### State Publication

```
RuntimeState Change
    ↓
orchestrator._publish_state_change()
    ├─ Convert to DashboardState
    └─ Call all registered callbacks:
        ├─ websocket.send_json() → Dashboard updates
        ├─ store.save_session_summary() → Persistent storage
        └─ Custom callbacks (logging, monitoring)
```

## Key Design Decisions

### 1. Single RuntimeState
- Single source of truth
- All components read/write through orchestrator
- No hidden state or caches
- State-safe via asyncio.Lock

### 2. Event-Driven Architecture
- ATEM connection state changes trigger updates
- Device state changes trigger engine tick
- Engine switches trigger statistics recording
- Changes trigger WebSocket publication

### 3. Non-Blocking Background Tasks
- Monitoring loop (device polling)
- Engine tick loop (state machine)
- Stats sync loop (persistence)
- All independent and async
- Cancellation-safe

### 4. Safe Edge Cases
- Zero eligible: retry with backoff
- One eligible: switch automatically
- Disconnect: stop auto-switching
- Signal loss: immediate fallback
- Operator change: detect and track

### 5. Production Readiness
- All async/await (no blocking I/O)
- Type hints throughout
- Comprehensive logging
- Error recovery strategies
- Testable with mocks

## Integration Points

### REST API Integration

```python
# routes/switcher.py
@router.post("/program/{input_index}")
async def set_program(
    input_index: int,
    orchestrator: ApplicationOrchestrator = Depends(get_orchestrator),
):
    await orchestrator.switch_to_input(input_index)
    state = await orchestrator.get_dashboard_state()
    return DashboardStateSchema.from_orm(state)
```

### WebSocket Integration

```python
# websocket handlers
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Subscribe to state changes
    orchestrator.register_state_callback(
        lambda state: websocket.send_json(DashboardStateSchema.from_orm(state))
    )
    
    while True:
        data = await websocket.receive_json()
        if data["action"] == "skip_current":
            await orchestrator.skip_current_camera()
```

### Persistence Integration

```python
# Database schema (SQLAlchemy)
class SwitchingEvent(Base):
    event_type: str  # 'switch', 'override', 'signal_loss'
    from_input: int
    to_input: int
    hold_duration: float
    timestamp: datetime

# Orchestrator records events
await storage.record_event(
    event_type="switch",
    from_input=old_input,
    to_input=new_input,
    reason="auto_switch",
)
```

## Component Responsibilities

### ApplicationOrchestrator
✓ Initialize subsystems
✓ Manage lifecycle
✓ Coordinate cross-system operations
✓ Handle errors and recovery
✓ Publish state changes
✓ Record statistics

### ATEMManager
✓ TCP connection to device
✓ Send commands (set_program_input, etc.)
✓ Poll device state
✓ Monitor connections
✓ Call connection callbacks

### SwitchingEngine
✓ Implement state machine
✓ Decide which camera to switch to
✓ Support multiple switch modes
✓ Handle operator overrides
✓ Track timing and eligibility

### StorageManager
✓ Load/save configuration
✓ Persist statistics
✓ Record event logs
✓ Track per-camera usage
✓ Provide historical data

## Testing Strategy

### Unit Tests
- Each component independently
- Mock dependencies
- Focus on business logic
- Fast execution

### Integration Tests
- Orchestrator + MockATEMAdapter
- Orchestrator + MockStorage
- Test initialization flow
- Test error recovery

### End-to-End Tests
- Real devices in lab
- Full workflow validation
- Performance benchmarking
- Load testing

## Deployment Checklist

- [ ] Database migrations run
- [ ] Environment variables set
- [ ] ATEM device accessible
- [ ] Storage writable
- [ ] Logging configured
- [ ] SSL certificates (if HTTPS)
- [ ] WebSocket proxying configured
- [ ] Error monitoring enabled
- [ ] Backups scheduled
- [ ] Documentation deployed
"""
