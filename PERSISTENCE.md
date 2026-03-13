"""Complete persistence layer documentation."""
# Persistence Layer Documentation

## Overview

The persistence layer provides production-grade, decoupled data storage for the ATEM Director application. It uses SQLite by default with support for PostgreSQL and other databases.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│            (API routes, services, engine)               │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              StorageManager (entry point)               │
│         (coordinates all repositories & sessions)       │
└─────────────────┬───────────────────────────────────────┘
                  │
         ┌────────┼────────┬─────────┬──────────┬────────┐
         ▼        ▼        ▼         ▼          ▼        ▼
    AppConfig  Presets  Intervals  InputOps  CameraStats Events
    Repository Repository Repository Repository Repository Repository
         │        │        │         │          │        │
         └────────┴────────┴─────────┴──────────┴────────┘
                  │
                  ▼
         ┌─────────────────────────┐
         │  AsyncSession (SQLAlchemy)│
         │  Database Engine         │
         └──────────┬────────────────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
      SQLite    PostgreSQL  Other DBs
```

## Database Models

### Core Entities

#### AppConfig
Stores application-wide settings and preferences.

```python
- atem_host: str (device IP)
- atem_port: int (device port)
- auto_switch_enabled: bool
- auto_switch_mode: str (balanced_random, weighted, etc.)
- safe_camera: int (fallback input)
- switch_interval_seconds: float
- min_hold_duration_seconds: float
- cooldown_seconds: float
- transition_mode: str (cut, mix)
- mix_duration_ms: int
```

#### SwitchingPreset
Predefined switching configurations.

```python
- name: str (unique)
- description: str
- program_input: int
- preview_input: int
- transition_mode: str
- transition_duration_ms: int
- enabled_inputs: list (JSON)
- switch_mode: str
- safe_camera: int
- weights: dict (JSON)
```

#### IntervalPoolEntry
Scheduling intervals for automatic switching.

```python
- name: str
- interval_seconds: float
- enabled: bool
- weight: float
```

#### InputOperatorState
Per-input enable/disable and cooldown tracking.

```python
- input_index: int (unique)
- enabled: bool
- cooldown_expires_at: datetime
- last_used_at: datetime
```

#### CameraStatistics
Per-camera usage metrics.

```python
- input_index: int (unique)
- switch_count: int
- total_program_seconds: float
- last_switched_at: datetime
- average_hold_seconds: float
- usage_percentage: float
```

#### SwitchingEvent
Audit trail of all switching operations.

```python
- event_type: str (switch, override, manual, error)
- from_input: int
- to_input: int
- reason: str
- hold_duration_seconds: float
- is_success: bool
- error_message: str
- metadata: dict (JSON)
- created_at: datetime
```

#### SessionSummary
Grouping of events into sessions.

```python
- session_name: str
- started_at: datetime
- ended_at: datetime
- total_switches: int
- total_duration_seconds: float
- auto_switch_enabled: bool
- average_hold_seconds: float
- notes: str
```

#### CumulativeStatistics
Rolling totals across all time.

```python
- total_switches_all_time: int
- total_program_seconds_all_time: float
- total_sessions: int
- average_hold_seconds: float
- most_used_camera: int
- least_used_camera: int
- last_reset_at: datetime
```

## Repository Pattern

Each entity has a dedicated repository providing type-safe CRUD operations.

### AppConfigRepository

```python
config = await repo.get_or_create_default()
updated = await repo.update(atem_host="10.0.0.1", auto_switch_enabled=True)
```

### PresetRepository

```python
preset = await repo.create("Scene A", 1, 2, transition_mode="cut")
preset = await repo.get_by_name("Scene A")
all_presets = await repo.get_all()
await repo.delete("Scene A")
```

### IntervalPoolRepository

```python
entry = await repo.create("30s", 30.0, weight=1.0)
enabled = await repo.get_all_enabled()
await repo.set_enabled("30s", False)
```

### InputOperatorStateRepository

```python
state = await repo.get_or_create(1)
await repo.set_enabled(1, False)
await repo.set_cooldown(1, 5.0)
await repo.mark_used(1)
```

### CameraStatisticsRepository

```python
stats = await repo.get_or_create(1)
await repo.record_switch(1, 30.0)
all_stats = await repo.get_all()
await repo.update_usage_percentages(total_seconds)
```

### SwitchingEventRepository

```python
event = await repo.create(
    event_type="switch",
    from_input=1,
    to_input=2,
    hold_duration_seconds=30.0,
)
recent = await repo.get_recent(limit=100)
events = await repo.get_by_date_range(start, end, event_type="switch")
```

### SessionSummaryRepository

```python
summary = await repo.create("Event 1", auto_switch_enabled=True)
await repo.end_session(summary.id, total_switches=42, average_hold_seconds=30.5)
recent = await repo.get_recent(limit=20)
```

### CumulativeStatisticsRepository

```python
stats = await repo.get_or_create()
await repo.update_from_switch(total_seconds, average_hold)
await repo.reset()
```

## StorageManager (High-Level Access)

The `StorageManager` provides coordinated access to all repositories and handles initialization.

```python
# Initialize
manager = StorageManager(session)
await manager.initialize_defaults()

# Load full config
config = await manager.load_config_from_storage()

# Backup runtime config
await manager.backup_config_to_storage(app_config, interval_pool)

# Record switching activity
await manager.record_switch_event(
    from_input=1,
    to_input=2,
    hold_duration=30.0,
    reason="auto",
)
```

## Database Configuration

### SQLite (Default - Local Development)

```python
# Auto-configures to ~/.atem_director/atem_director.db
database_url = "sqlite+aiosqlite:///~/.atem_director/atem_director.db"
```

### PostgreSQL (Production)

```python
database_url = "postgresql+asyncpg://user:password@localhost/atem_director"
```

### Other Databases

Any SQLAlchemy-supported database works:
- MySQL: `mysql+aiomysql://user:password@localhost/atem_director`
- Oracle: `oracle+cx_oracle://user:password@localhost/atem_director`

## Initialization & Startup

### First Launch

```python
from atem_director.persistence.database import init_db
from atem_director.persistence.storage import StorageManager

# Initialize database (creates tables)
await init_db()

# Create session and storage manager
async with get_db_session() as session:
    manager = StorageManager(session)
    
    # Initialize with defaults
    await manager.initialize_defaults()
    
    # Load config into runtime
    config = await manager.load_config_from_storage()
```

### Default Initialization

When `initialize_defaults()` is called:

1. Creates AppConfig with defaults if not exists
2. Creates CumulativeStatistics if not exists
3. Seeds IntervalPoolEntry with standard intervals (15s, 30s, 45s, 60s)

### Safe Startup Loading

```python
async def safe_startup():
    """Startup with fallback to hardcoded defaults."""
    try:
        async with get_db_session() as session:
            manager = StorageManager(session)
            config = await manager.load_config_from_storage()
            return config
    except Exception as e:
        logger.warning("Failed to load from storage, using defaults", error=str(e))
        return get_hardcoded_defaults()
```

## Persistence Patterns

### Recording a Switch

```python
async def on_switch_event(from_input: int, to_input: int, duration: float):
    async with get_db_session() as session:
        manager = StorageManager(session)
        await manager.record_switch_event(
            from_input=from_input,
            to_input=to_input,
            hold_duration=duration,
            reason="auto_switch",
        )
```

### Backing Up Current Configuration

```python
async def backup_current_state():
    """Save runtime config back to database."""
    app_config = {
        "atem_host": "192.168.1.100",
        "auto_switch_enabled": True,
        "auto_switch_mode": "balanced_random",
        # ... other fields
    }
    
    interval_pool = [
        {"name": "15s", "interval_seconds": 15.0, "enabled": True},
        # ... other intervals
    ]
    
    async with get_db_session() as session:
        manager = StorageManager(session)
        await manager.backup_config_to_storage(app_config, interval_pool)
```

### Querying Statistics

```python
async def get_camera_usage():
    """Get per-camera usage statistics."""
    async with get_db_session() as session:
        repo = CameraStatisticsRepository(session)
        all_stats = await repo.get_all()
        
        for stats in all_stats:
            print(f"Camera {stats.input_index}: "
                  f"{stats.switch_count} switches, "
                  f"{stats.usage_percentage:.1f}% usage")
```

### Event Auditing

```python
async def get_daily_report():
    """Get switching events for today."""
    from datetime import date
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    async with get_db_session() as session:
        repo = SwitchingEventRepository(session)
        events = await repo.get_by_date_range(today_start, today_end)
        
        for event in events:
            print(f"{event.created_at}: {event.from_input} → {event.to_input}")
```

## Design Rules (Enforced)

1. **No coupling to routes** - Repositories are pure data access, no HTTP semantics
2. **Modular repositories** - Each repository is independent, can be used separately
3. **Strong typing** - Full type hints throughout
4. **Async/await** - Built for async Python applications
5. **Session management** - Repositories don't manage sessions, they receive them
6. **No mutations** - State only changes via explicit repository methods
7. **Fail-safe defaults** - AppConfig provides sensible defaults if DB unavailable

## Testing

All repositories are testable with in-memory SQLite:

```python
@pytest.fixture
async def test_db():
    """Create in-memory test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        yield session
```

## Statistics Maintenance

Statistics are maintained automatically:

- **Per-Camera Stats**: Updated on each switch via `record_switch()`
- **Usage Percentages**: Updated after each switch calculation
- **Cumulative Stats**: Updated incrementally on each switch
- **Average Hold**: Recalculated using running average formula

## Cleanup & Maintenance

### Reset Cumulative Statistics

```python
async with get_db_session() as session:
    repo = CumulativeStatisticsRepository(session)
    await repo.reset()
```

### Archive Old Events

```python
# Implement retention policy (not provided - application-specific)
one_month_ago = datetime.now() - timedelta(days=30)
# Query and delete events before this date
```

## Migration from Other Databases

Since SQLAlchemy is agnostic:

1. Define `DATABASE_URL` pointing to new database
2. Call `init_db(database_url)` - tables are created
3. Migrate data using standard ETL practices

## Summary

The persistence layer provides:
- ✅ SQLite by default for local development
- ✅ PostgreSQL support for production
- ✅ Type-safe repository pattern
- ✅ Complete statistics tracking
- ✅ Event audit trail
- ✅ Preset management
- ✅ Session grouping
- ✅ Sensible defaults
- ✅ Safe startup loading
- ✅ Comprehensive testing support
