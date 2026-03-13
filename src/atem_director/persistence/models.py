"""Database models (ORM)."""
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, Integer, Boolean, Text, Float, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class AppConfig(Base):
    """Application configuration persistence."""
    __tablename__ = "app_config"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    atem_host: Mapped[str] = mapped_column(String(255), default="192.168.1.100")
    atem_port: Mapped[int] = mapped_column(Integer, default=21124)
    auto_switch_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_switch_mode: Mapped[str] = mapped_column(String(50), default="balanced_random")
    safe_camera: Mapped[int] = mapped_column(Integer, default=1)
    switch_interval_seconds: Mapped[float] = mapped_column(Float, default=30.0)
    min_hold_duration_seconds: Mapped[float] = mapped_column(Float, default=10.0)
    cooldown_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    transition_mode: Mapped[str] = mapped_column(String(20), default="cut")
    mix_duration_ms: Mapped[int] = mapped_column(Integer, default=300)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class SwitchingPreset(Base):
    """Switching preset model."""
    __tablename__ = "switching_presets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    program_input: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_input: Mapped[int] = mapped_column(Integer, nullable=False)
    transition_mode: Mapped[str] = mapped_column(String(20), default="cut")
    transition_duration_ms: Mapped[int] = mapped_column(Integer, default=300)
    enabled_inputs: Mapped[str] = mapped_column(Text, nullable=True)  # JSON-serialized list
    switch_mode: Mapped[str] = mapped_column(String(50), nullable=True)
    safe_camera: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-serialized
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class IntervalPoolEntry(Base):
    """Interval pool entry for scheduling."""
    __tablename__ = "interval_pool_entries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    interval_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class InputOperatorState(Base):
    """Per-input operator enable/disable state."""
    __tablename__ = "input_operator_states"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_index: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class CameraStatistics(Base):
    """Per-camera usage statistics."""
    __tablename__ = "camera_statistics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_index: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    switch_count: Mapped[int] = mapped_column(Integer, default=0)
    total_program_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    last_switched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    average_hold_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    usage_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class SwitchingEvent(Base):
    """Event log for switching operations."""
    __tablename__ = "switching_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'switch', 'override', 'manual', 'error'
    from_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hold_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-serialized
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class SessionSummary(Base):
    """Summary of a switching session."""
    __tablename__ = "session_summaries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_switches: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    auto_switch_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    average_hold_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class CumulativeStatistics(Base):
    """Cumulative statistics across all sessions."""
    __tablename__ = "cumulative_statistics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    total_switches_all_time: Mapped[int] = mapped_column(Integer, default=0)
    total_program_seconds_all_time: Mapped[float] = mapped_column(Float, default=0.0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    average_hold_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    most_used_camera: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    least_used_camera: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_reset_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Session(Base):
    """User session model."""
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
