"""Runtime state model for application state management.

This module defines the complete runtime state of the ATEM Director application,
including device state, switching engine state, statistics, and dashboard state.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum

from atem_director.atem_layer.models import (
    ATEMStatus,
    SwitcherState,
    ConnectionState,
)
from atem_director.engine.switching import SwitchingState


class OperationMode(str, Enum):
    """Application operation mode."""
    MANUAL = "manual"  # User controls switches
    AUTO = "auto"  # Automatic switching enabled
    FAILSAFE = "failsafe"  # Restricted mode after errors


@dataclass
class CameraState:
    """State of a single camera input."""
    input_index: int
    enabled: bool = True
    has_signal: bool = False
    is_current_program: bool = False
    is_current_preview: bool = False
    is_locked: bool = False
    lock_expires_at: Optional[datetime] = None
    cooldown_expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    total_switches: int = 0
    total_program_seconds: float = 0.0


@dataclass
class SwitchingSessionStats:
    """Statistics for current switching session."""
    started_at: datetime
    total_switches: int = 0
    last_switch_at: Optional[datetime] = None
    last_switched_from: Optional[int] = None
    last_switched_to: Optional[int] = None
    average_hold_seconds: float = 0.0
    total_hold_seconds: float = 0.0
    hold_counts: int = 0


@dataclass
class DashboardState:
    """Complete dashboard/UI state."""
    # Device state
    atem_status: ATEMStatus
    switcher_state: SwitcherState
    
    # Switching engine state
    engine_state: SwitchingState
    operation_mode: OperationMode
    
    # Camera states
    camera_states: Dict[int, CameraState] = field(default_factory=dict)
    
    # Session statistics
    session_stats: Optional[SwitchingSessionStats] = None
    
    # Current configuration
    auto_switch_enabled: bool = False
    current_switch_mode: str = "balanced_random"
    current_interval_seconds: float = 30.0
    
    # UI-relevant state
    is_initializing: bool = True
    last_error: Optional[str] = None
    last_update_at: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update last update timestamp."""
        self.last_update_at = datetime.now()


@dataclass
class RuntimeState:
    """Complete runtime state of the application.
    
    This is the single source of truth for the entire application state.
    All components read from and write to this state through the orchestrator.
    """
    # Device connection
    atem_manager: Optional[object] = None
    atem_status: ATEMStatus = field(default_factory=ATEMStatus)
    switcher_state: SwitcherState = field(default_factory=SwitcherState)
    
    # Switching engine
    switching_engine: Optional[object] = None
    engine_state: SwitchingState = SwitchingState.IDLE
    operation_mode: OperationMode = OperationMode.MANUAL
    
    # Application settings
    auto_switch_enabled: bool = False
    current_switch_mode: str = "balanced_random"
    safe_camera: int = 1
    
    # Per-input state
    camera_states: Dict[int, CameraState] = field(default_factory=dict)
    
    # Current session
    session_active: bool = False
    session_started_at: Optional[datetime] = None
    session_stats: Optional[SwitchingSessionStats] = None
    
    # System state
    is_initialized: bool = False
    is_initializing: bool = False
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    # Tracking
    total_initialization_attempts: int = 0
    last_update_at: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update last update timestamp."""
        self.last_update_at = datetime.now()
    
    def to_dashboard_state(self) -> DashboardState:
        """Convert runtime state to dashboard state for UI."""
        return DashboardState(
            atem_status=self.atem_status,
            switcher_state=self.switcher_state,
            engine_state=self.engine_state,
            operation_mode=self.operation_mode,
            camera_states=dict(self.camera_states),
            session_stats=self.session_stats,
            auto_switch_enabled=self.auto_switch_enabled,
            current_switch_mode=self.current_switch_mode,
            current_interval_seconds=0.0,  # Would load from config
            is_initializing=self.is_initializing,
            last_error=self.last_error,
            last_update_at=self.last_update_at,
        )
