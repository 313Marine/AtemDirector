"""Repository pattern for data persistence.

This layer provides type-safe, decoupled access to all persisted entities.
Repositories are stateless services that handle all CRUD operations and queries.
"""
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from sqlalchemy.orm import selectinload

from atem_director.logging import get_logger
from atem_director.persistence.models import (
    AppConfig,
    SwitchingPreset,
    IntervalPoolEntry,
    InputOperatorState,
    CameraStatistics,
    SwitchingEvent,
    SessionSummary,
    CumulativeStatistics,
)

logger = get_logger(__name__)


class AppConfigRepository:
    """Repository for application configuration."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def get_or_create_default(self) -> AppConfig:
        """Get app config or create with defaults if not exists."""
        stmt = select(AppConfig).limit(1)
        result = await self.session.execute(stmt)
        config = result.scalars().first()
        
        if config is None:
            config = AppConfig()
            self.session.add(config)
            await self.session.commit()
            logger.info("Created default app config")
        
        return config
    
    async def update(self, **kwargs: Any) -> AppConfig:
        """Update app config with provided fields.
        
        Args:
            **kwargs: Fields to update
            
        Returns:
            Updated AppConfig
        """
        config = await self.get_or_create_default()
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.now()
        await self.session.commit()
        logger.info("Updated app config", fields=list(kwargs.keys()))
        
        return config


class PresetRepository:
    """Repository for switching presets."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create(
        self,
        name: str,
        program_input: int,
        preview_input: int,
        **kwargs: Any,
    ) -> SwitchingPreset:
        """Create a new preset.
        
        Args:
            name: Preset name
            program_input: Program input index
            preview_input: Preview input index
            **kwargs: Additional fields
            
        Returns:
            Created preset
        """
        preset = SwitchingPreset(
            name=name,
            program_input=program_input,
            preview_input=preview_input,
            **kwargs,
        )
        
        self.session.add(preset)
        await self.session.commit()
        logger.info("Created preset", name=name)
        
        return preset
    
    async def get_by_name(self, name: str) -> Optional[SwitchingPreset]:
        """Get preset by name.
        
        Args:
            name: Preset name
            
        Returns:
            Preset or None
        """
        stmt = select(SwitchingPreset).where(SwitchingPreset.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_all(self) -> List[SwitchingPreset]:
        """Get all presets.
        
        Returns:
            List of presets
        """
        stmt = select(SwitchingPreset).order_by(SwitchingPreset.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def delete(self, name: str) -> bool:
        """Delete preset by name.
        
        Args:
            name: Preset name
            
        Returns:
            True if deleted, False if not found
        """
        preset = await self.get_by_name(name)
        if preset:
            await self.session.delete(preset)
            await self.session.commit()
            logger.info("Deleted preset", name=name)
            return True
        return False


class IntervalPoolRepository:
    """Repository for interval pool entries."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create(
        self,
        name: str,
        interval_seconds: float,
        enabled: bool = True,
        weight: float = 1.0,
    ) -> IntervalPoolEntry:
        """Create interval pool entry.
        
        Args:
            name: Entry name
            interval_seconds: Interval in seconds
            enabled: Is enabled
            weight: Weight for weighted selection
            
        Returns:
            Created entry
        """
        entry = IntervalPoolEntry(
            name=name,
            interval_seconds=interval_seconds,
            enabled=enabled,
            weight=weight,
        )
        
        self.session.add(entry)
        await self.session.commit()
        logger.info("Created interval pool entry", name=name)
        
        return entry
    
    async def get_all_enabled(self) -> List[IntervalPoolEntry]:
        """Get all enabled interval entries.
        
        Returns:
            List of enabled entries
        """
        stmt = select(IntervalPoolEntry).where(
            IntervalPoolEntry.enabled == True
        ).order_by(IntervalPoolEntry.name)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def set_enabled(self, name: str, enabled: bool) -> Optional[IntervalPoolEntry]:
        """Set enabled status for entry.
        
        Args:
            name: Entry name
            enabled: Enable/disable
            
        Returns:
            Updated entry or None
        """
        stmt = select(IntervalPoolEntry).where(IntervalPoolEntry.name == name)
        result = await self.session.execute(stmt)
        entry = result.scalars().first()
        
        if entry:
            entry.enabled = enabled
            entry.updated_at = datetime.now()
            await self.session.commit()
            logger.info("Updated interval pool entry", name=name, enabled=enabled)
        
        return entry


class InputOperatorStateRepository:
    """Repository for input operator states."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def get_or_create(self, input_index: int) -> InputOperatorState:
        """Get or create operator state for input.
        
        Args:
            input_index: Input index
            
        Returns:
            InputOperatorState
        """
        stmt = select(InputOperatorState).where(
            InputOperatorState.input_index == input_index
        )
        result = await self.session.execute(stmt)
        state = result.scalars().first()
        
        if state is None:
            state = InputOperatorState(input_index=input_index)
            self.session.add(state)
            await self.session.commit()
        
        return state
    
    async def set_enabled(self, input_index: int, enabled: bool) -> InputOperatorState:
        """Set enabled status for input.
        
        Args:
            input_index: Input index
            enabled: Enable/disable
            
        Returns:
            Updated state
        """
        state = await self.get_or_create(input_index)
        state.enabled = enabled
        state.updated_at = datetime.now()
        await self.session.commit()
        
        logger.info("Set input operator state", input_index=input_index, enabled=enabled)
        
        return state
    
    async def set_cooldown(self, input_index: int, cooldown_seconds: float) -> InputOperatorState:
        """Set cooldown expiration for input.
        
        Args:
            input_index: Input index
            cooldown_seconds: Cooldown duration
            
        Returns:
            Updated state
        """
        state = await self.get_or_create(input_index)
        state.cooldown_expires_at = datetime.now() + timedelta(seconds=cooldown_seconds)
        state.updated_at = datetime.now()
        await self.session.commit()
        
        logger.info("Set input cooldown", input_index=input_index, seconds=cooldown_seconds)
        
        return state
    
    async def mark_used(self, input_index: int) -> InputOperatorState:
        """Mark input as used now.
        
        Args:
            input_index: Input index
            
        Returns:
            Updated state
        """
        state = await self.get_or_create(input_index)
        state.last_used_at = datetime.now()
        state.updated_at = datetime.now()
        await self.session.commit()
        
        return state


class CameraStatisticsRepository:
    """Repository for camera statistics."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def get_or_create(self, input_index: int) -> CameraStatistics:
        """Get or create stats for camera.
        
        Args:
            input_index: Input/camera index
            
        Returns:
            CameraStatistics
        """
        stmt = select(CameraStatistics).where(
            CameraStatistics.input_index == input_index
        )
        result = await self.session.execute(stmt)
        stats = result.scalars().first()
        
        if stats is None:
            stats = CameraStatistics(input_index=input_index)
            self.session.add(stats)
            await self.session.commit()
        
        return stats
    
    async def record_switch(
        self,
        input_index: int,
        hold_duration_seconds: float,
    ) -> CameraStatistics:
        """Record a switch to camera.
        
        Args:
            input_index: Input/camera index
            hold_duration_seconds: How long it was held
            
        Returns:
            Updated statistics
        """
        stats = await self.get_or_create(input_index)
        
        stats.switch_count += 1
        stats.total_program_seconds += hold_duration_seconds
        stats.last_switched_at = datetime.now()
        
        # Update average
        if stats.average_hold_seconds is None:
            stats.average_hold_seconds = hold_duration_seconds
        else:
            stats.average_hold_seconds = (
                (stats.average_hold_seconds * (stats.switch_count - 1) + hold_duration_seconds)
                / stats.switch_count
            )
        
        stats.updated_at = datetime.now()
        await self.session.commit()
        
        return stats
    
    async def get_all(self) -> List[CameraStatistics]:
        """Get all camera statistics.
        
        Returns:
            List of statistics
        """
        stmt = select(CameraStatistics).order_by(CameraStatistics.input_index)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_usage_percentages(self, total_seconds: float) -> None:
        """Update usage percentages for all cameras.
        
        Args:
            total_seconds: Total program seconds across all cameras
        """
        if total_seconds <= 0:
            return
        
        all_stats = await self.get_all()
        for stats in all_stats:
            stats.usage_percentage = (stats.total_program_seconds / total_seconds) * 100
        
        await self.session.commit()


class SwitchingEventRepository:
    """Repository for switching events."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create(
        self,
        event_type: str,
        from_input: Optional[int] = None,
        to_input: Optional[int] = None,
        reason: Optional[str] = None,
        hold_duration_seconds: Optional[float] = None,
        is_success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwitchingEvent:
        """Create switching event.
        
        Args:
            event_type: Type of event (switch, override, manual, error)
            from_input: Previous input
            to_input: New input
            reason: Reason for event
            hold_duration_seconds: Duration held
            is_success: Was successful
            error_message: Error if applicable
            metadata: Extra data (as dict, will be JSON-serialized)
            
        Returns:
            Created event
        """
        event = SwitchingEvent(
            event_type=event_type,
            from_input=from_input,
            to_input=to_input,
            reason=reason,
            hold_duration_seconds=hold_duration_seconds,
            is_success=is_success,
            error_message=error_message,
            metadata=json.dumps(metadata) if metadata else None,
        )
        
        self.session.add(event)
        await self.session.commit()
        
        logger.info(
            "Recorded switching event",
            event_type=event_type,
            from_input=from_input,
            to_input=to_input,
            success=is_success,
        )
        
        return event
    
    async def get_recent(self, limit: int = 100) -> List[SwitchingEvent]:
        """Get recent events.
        
        Args:
            limit: Number of events to return
            
        Returns:
            List of recent events
        """
        stmt = select(SwitchingEvent).order_by(
            desc(SwitchingEvent.created_at)
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        event_type: Optional[str] = None,
    ) -> List[SwitchingEvent]:
        """Get events in date range.
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            event_type: Filter by event type
            
        Returns:
            List of matching events
        """
        stmt = select(SwitchingEvent).where(
            and_(
                SwitchingEvent.created_at >= start_date,
                SwitchingEvent.created_at <= end_date,
            )
        )
        
        if event_type:
            stmt = stmt.where(SwitchingEvent.event_type == event_type)
        
        stmt = stmt.order_by(desc(SwitchingEvent.created_at))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SessionSummaryRepository:
    """Repository for session summaries."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create(self, session_name: str, **kwargs: Any) -> SessionSummary:
        """Create session summary.
        
        Args:
            session_name: Name of session
            **kwargs: Additional fields
            
        Returns:
            Created summary
        """
        summary = SessionSummary(session_name=session_name, **kwargs)
        self.session.add(summary)
        await self.session.commit()
        
        logger.info("Created session summary", name=session_name)
        
        return summary
    
    async def end_session(
        self,
        session_id: int,
        total_switches: int,
        average_hold_seconds: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[SessionSummary]:
        """End a session.
        
        Args:
            session_id: Session ID
            total_switches: Total switches in session
            average_hold_seconds: Average hold duration
            notes: Session notes
            
        Returns:
            Updated summary or None
        """
        stmt = select(SessionSummary).where(SessionSummary.id == session_id)
        result = await self.session.execute(stmt)
        summary = result.scalars().first()
        
        if summary:
            summary.ended_at = datetime.now()
            summary.total_switches = total_switches
            summary.total_duration_seconds = (
                (summary.ended_at - summary.started_at).total_seconds()
            )
            summary.average_hold_seconds = average_hold_seconds
            summary.notes = notes
            
            await self.session.commit()
            logger.info("Ended session", id=session_id)
        
        return summary
    
    async def get_recent(self, limit: int = 20) -> List[SessionSummary]:
        """Get recent sessions.
        
        Args:
            limit: Number of sessions
            
        Returns:
            List of recent sessions
        """
        stmt = select(SessionSummary).order_by(
            desc(SessionSummary.started_at)
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()


class CumulativeStatisticsRepository:
    """Repository for cumulative statistics."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def get_or_create(self) -> CumulativeStatistics:
        """Get cumulative stats or create if not exists.
        
        Returns:
            CumulativeStatistics
        """
        stmt = select(CumulativeStatistics).limit(1)
        result = await self.session.execute(stmt)
        stats = result.scalars().first()
        
        if stats is None:
            stats = CumulativeStatistics()
            self.session.add(stats)
            await self.session.commit()
        
        return stats
    
    async def update_from_switch(
        self,
        total_program_seconds: float,
        average_hold_seconds: float,
    ) -> CumulativeStatistics:
        """Update cumulative stats after a switch.
        
        Args:
            total_program_seconds: New total program seconds
            average_hold_seconds: New average hold
            
        Returns:
            Updated statistics
        """
        stats = await self.get_or_create()
        
        stats.total_switches_all_time += 1
        stats.total_program_seconds_all_time = total_program_seconds
        stats.average_hold_seconds = average_hold_seconds
        stats.updated_at = datetime.now()
        
        await self.session.commit()
        
        return stats
    
    async def reset(self) -> CumulativeStatistics:
        """Reset cumulative statistics.
        
        Returns:
            Reset statistics
        """
        stats = await self.get_or_create()
        
        stats.total_switches_all_time = 0
        stats.total_program_seconds_all_time = 0.0
        stats.total_sessions = 0
        stats.average_hold_seconds = 0.0
        stats.most_used_camera = None
        stats.least_used_camera = None
        stats.last_reset_at = datetime.now()
        stats.updated_at = datetime.now()
        
        await self.session.commit()
        logger.info("Reset cumulative statistics")
        
        return stats
