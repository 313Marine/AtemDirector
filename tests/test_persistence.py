"""Tests for persistence layer."""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from atem_director.persistence.models import Base
from atem_director.persistence.repository import (
    AppConfigRepository,
    PresetRepository,
    IntervalPoolRepository,
    InputOperatorStateRepository,
    CameraStatisticsRepository,
    SwitchingEventRepository,
)
from atem_director.persistence.storage import StorageManager


@pytest.fixture
async def test_db():
    """Create in-memory SQLite test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_app_config_repository(test_db):
    """Test app config repository."""
    repo = AppConfigRepository(test_db)
    
    # Get or create default
    config = await repo.get_or_create_default()
    assert config.id is not None
    assert config.atem_host == "192.168.1.100"
    
    # Update
    updated = await repo.update(atem_host="10.0.0.1", auto_switch_enabled=True)
    assert updated.atem_host == "10.0.0.1"
    assert updated.auto_switch_enabled is True


@pytest.mark.asyncio
async def test_preset_repository(test_db):
    """Test preset repository."""
    repo = PresetRepository(test_db)
    
    # Create preset
    preset = await repo.create(
        name="Test Preset",
        program_input=1,
        preview_input=2,
        transition_mode="cut",
    )
    assert preset.id is not None
    assert preset.name == "Test Preset"
    
    # Get by name
    retrieved = await repo.get_by_name("Test Preset")
    assert retrieved is not None
    assert retrieved.program_input == 1
    
    # Get all
    all_presets = await repo.get_all()
    assert len(all_presets) == 1
    
    # Delete
    deleted = await repo.delete("Test Preset")
    assert deleted is True
    
    all_presets = await repo.get_all()
    assert len(all_presets) == 0


@pytest.mark.asyncio
async def test_interval_pool_repository(test_db):
    """Test interval pool repository."""
    repo = IntervalPoolRepository(test_db)
    
    # Create entries
    entry1 = await repo.create("15s", 15.0)
    entry2 = await repo.create("30s", 30.0, enabled=False)
    
    # Get all enabled
    enabled = await repo.get_all_enabled()
    assert len(enabled) == 1
    assert enabled[0].name == "15s"
    
    # Set enabled
    await repo.set_enabled("30s", True)
    enabled = await repo.get_all_enabled()
    assert len(enabled) == 2


@pytest.mark.asyncio
async def test_input_operator_state_repository(test_db):
    """Test input operator state repository."""
    repo = InputOperatorStateRepository(test_db)
    
    # Get or create
    state = await repo.get_or_create(1)
    assert state.input_index == 1
    assert state.enabled is True
    
    # Set disabled
    await repo.set_enabled(1, False)
    state = await repo.get_or_create(1)
    assert state.enabled is False
    
    # Set cooldown
    await repo.set_cooldown(1, 5.0)
    state = await repo.get_or_create(1)
    assert state.cooldown_expires_at is not None
    
    # Mark used
    await repo.mark_used(1)
    state = await repo.get_or_create(1)
    assert state.last_used_at is not None


@pytest.mark.asyncio
async def test_camera_statistics_repository(test_db):
    """Test camera statistics repository."""
    repo = CameraStatisticsRepository(test_db)
    
    # Get or create
    stats = await repo.get_or_create(1)
    assert stats.switch_count == 0
    assert stats.total_program_seconds == 0.0
    
    # Record switch
    await repo.record_switch(1, 30.0)
    stats = await repo.get_or_create(1)
    assert stats.switch_count == 1
    assert stats.total_program_seconds == 30.0
    assert stats.average_hold_seconds == 30.0
    
    # Record another switch
    await repo.record_switch(1, 45.0)
    stats = await repo.get_or_create(1)
    assert stats.switch_count == 2
    assert stats.total_program_seconds == 75.0
    assert stats.average_hold_seconds == 37.5
    
    # Update usage percentages
    await repo.update_usage_percentages(75.0)
    stats = await repo.get_or_create(1)
    assert stats.usage_percentage == 100.0


@pytest.mark.asyncio
async def test_switching_event_repository(test_db):
    """Test switching event repository."""
    repo = SwitchingEventRepository(test_db)
    
    # Create event
    event = await repo.create(
        event_type="switch",
        from_input=1,
        to_input=2,
        reason="auto",
        hold_duration_seconds=30.0,
    )
    assert event.id is not None
    assert event.event_type == "switch"
    
    # Get recent
    recent = await repo.get_recent(limit=10)
    assert len(recent) == 1
    
    # Get by date range
    start = datetime.now() - timedelta(hours=1)
    end = datetime.now() + timedelta(hours=1)
    events = await repo.get_by_date_range(start, end, event_type="switch")
    assert len(events) == 1


@pytest.mark.asyncio
async def test_storage_manager_initialization(test_db):
    """Test storage manager initialization."""
    manager = StorageManager(test_db)
    
    # Initialize defaults
    await manager.initialize_defaults()
    
    # Verify defaults created
    config = await manager.app_config.get_or_create_default()
    assert config is not None
    
    # Verify interval pool created
    intervals = await manager.interval_pool.get_all_enabled()
    assert len(intervals) > 0


@pytest.mark.asyncio
async def test_storage_manager_load_config(test_db):
    """Test loading config from storage."""
    manager = StorageManager(test_db)
    await manager.initialize_defaults()
    
    # Load config
    config = await manager.load_config_from_storage()
    
    assert "app_config" in config
    assert "interval_pool" in config
    assert "camera_stats" in config
    assert "cumulative_stats" in config
    
    assert config["app_config"]["atem_host"] == "192.168.1.100"
    assert len(config["interval_pool"]) > 0


@pytest.mark.asyncio
async def test_storage_manager_record_switch(test_db):
    """Test recording switch events."""
    manager = StorageManager(test_db)
    await manager.initialize_defaults()
    
    # Record switch
    await manager.record_switch_event(1, 2, 30.0, reason="auto")
    
    # Check event recorded
    events = await manager.switching_events.get_recent(limit=1)
    assert len(events) == 1
    assert events[0].from_input == 1
    assert events[0].to_input == 2
    
    # Check camera stats updated
    stats = await manager.camera_stats.get_or_create(2)
    assert stats.switch_count == 1
    assert stats.total_program_seconds == 30.0
