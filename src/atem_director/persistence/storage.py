"""High-level storage manager for coordinated access to all repositories.

This manager ensures repositories are created with valid sessions and handles
initialization and safe startup procedures.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from atem_director.logging import get_logger
from atem_director.persistence.repository import (
    AppConfigRepository,
    PresetRepository,
    IntervalPoolRepository,
    InputOperatorStateRepository,
    CameraStatisticsRepository,
    SwitchingEventRepository,
    SessionSummaryRepository,
    CumulativeStatisticsRepository,
)

logger = get_logger(__name__)


class StorageManager:
    """Unified storage access manager.
    
    Provides repositories for all entities and coordinates initialization.
    All repositories share the same database session lifecycle.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize storage manager.
        
        Args:
            session: Database session
        """
        self.session = session
        
        # Initialize repositories
        self.app_config = AppConfigRepository(session)
        self.presets = PresetRepository(session)
        self.interval_pool = IntervalPoolRepository(session)
        self.input_states = InputOperatorStateRepository(session)
        self.camera_stats = CameraStatisticsRepository(session)
        self.switching_events = SwitchingEventRepository(session)
        self.sessions = SessionSummaryRepository(session)
        self.cumulative_stats = CumulativeStatisticsRepository(session)
    
    async def initialize_defaults(self) -> None:
        """Initialize default configuration and data if not present.
        
        This should be called once on first startup to seed the database
        with sensible defaults.
        """
        logger.info("Initializing storage defaults")
        
        # Ensure app config exists with defaults
        config = await self.app_config.get_or_create_default()
        logger.info("App config ready", id=config.id)
        
        # Ensure cumulative stats exist
        cum_stats = await self.cumulative_stats.get_or_create()
        logger.info("Cumulative statistics ready", id=cum_stats.id)
        
        # Create default interval pool if empty
        enabled_entries = await self.interval_pool.get_all_enabled()
        if not enabled_entries:
            logger.info("Creating default interval pool entries")
            
            default_intervals = [
                ("15s", 15.0, 1.0),
                ("30s", 30.0, 1.0),
                ("45s", 45.0, 0.8),
                ("60s", 60.0, 0.6),
            ]
            
            for name, seconds, weight in default_intervals:
                await self.interval_pool.create(
                    name=name,
                    interval_seconds=seconds,
                    weight=weight,
                )
        
        logger.info("Storage initialization complete")
    
    async def load_config_from_storage(self) -> dict:
        """Load all configuration from storage.
        
        Returns:
            Dictionary with all config and state
        """
        config = await self.app_config.get_or_create_default()
        enabled_intervals = await self.interval_pool.get_all_enabled()
        all_camera_stats = await self.camera_stats.get_all()
        cum_stats = await self.cumulative_stats.get_or_create()
        
        return {
            "app_config": {
                "atem_host": config.atem_host,
                "atem_port": config.atem_port,
                "auto_switch_enabled": config.auto_switch_enabled,
                "auto_switch_mode": config.auto_switch_mode,
                "safe_camera": config.safe_camera,
                "switch_interval_seconds": config.switch_interval_seconds,
                "min_hold_duration_seconds": config.min_hold_duration_seconds,
                "cooldown_seconds": config.cooldown_seconds,
                "transition_mode": config.transition_mode,
                "mix_duration_ms": config.mix_duration_ms,
            },
            "interval_pool": [
                {
                    "name": entry.name,
                    "interval_seconds": entry.interval_seconds,
                    "enabled": entry.enabled,
                    "weight": entry.weight,
                }
                for entry in enabled_intervals
            ],
            "camera_stats": [
                {
                    "input_index": stats.input_index,
                    "switch_count": stats.switch_count,
                    "total_program_seconds": stats.total_program_seconds,
                    "average_hold_seconds": stats.average_hold_seconds,
                    "usage_percentage": stats.usage_percentage,
                    "last_switched_at": stats.last_switched_at.isoformat() if stats.last_switched_at else None,
                }
                for stats in all_camera_stats
            ],
            "cumulative_stats": {
                "total_switches_all_time": cum_stats.total_switches_all_time,
                "total_program_seconds_all_time": cum_stats.total_program_seconds_all_time,
                "average_hold_seconds": cum_stats.average_hold_seconds,
                "total_sessions": cum_stats.total_sessions,
            },
        }
    
    async def backup_config_to_storage(
        self,
        app_config: dict,
        interval_pool: list,
    ) -> None:
        """Backup current runtime config to storage.
        
        Args:
            app_config: Application config dict
            interval_pool: List of interval pool configs
        """
        # Update app config
        await self.app_config.update(**app_config)
        
        # Update interval pool (disable all, then enable active ones)
        all_entries = await self.interval_pool.get_all_enabled()
        for entry in all_entries:
            await self.interval_pool.set_enabled(entry.name, False)
        
        # Enable the active ones from interval_pool
        for pool_config in interval_pool:
            name = pool_config.get("name")
            if name:
                await self.interval_pool.set_enabled(name, True)
        
        logger.info("Backed up config to storage")
    
    async def record_switch_event(
        self,
        from_input: int,
        to_input: int,
        hold_duration: float,
        reason: Optional[str] = None,
    ) -> None:
        """Record a switching event and update stats.
        
        Args:
            from_input: Previous input
            to_input: New input
            hold_duration: How long the previous was on screen
            reason: Reason for switch
        """
        # Record event
        await self.switching_events.create(
            event_type="switch",
            from_input=from_input,
            to_input=to_input,
            hold_duration_seconds=hold_duration,
            reason=reason,
        )
        
        # Update camera stats for the new input
        await self.camera_stats.record_switch(to_input, hold_duration)
        
        # Update cumulative stats
        all_stats = await self.camera_stats.get_all()
        total_program_seconds = sum(s.total_program_seconds for s in all_stats)
        
        if all_stats:
            avg_hold = sum(s.average_hold_seconds for s in all_stats if s.average_hold_seconds) / len(all_stats)
        else:
            avg_hold = 0.0
        
        # Update usage percentages
        await self.camera_stats.update_usage_percentages(total_program_seconds)
        
        # Update cumulative stats
        await self.cumulative_stats.update_from_switch(total_program_seconds, avg_hold)
    
    async def get_session_summary(
        self,
        session_id: int,
    ) -> Optional[dict]:
        """Get summary of a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session summary dict or None
        """
        # This would query the specific session
        # For now, return None as placeholder
        return None
