"""API request/response schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)


class UserLoginRequest(BaseModel):
    """User login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ============================================================================
# Control Operation Schemas
# ============================================================================

class SkipCurrentRequest(BaseModel):
    """Skip current camera request."""
    reason: Optional[str] = None


class SkipNextRequest(BaseModel):
    """Skip next scheduled switch request."""
    reason: Optional[str] = None


class ExtendCurrentRequest(BaseModel):
    """Extend current camera hold time request."""
    seconds: int = Field(..., ge=10, le=600)


class HoldCurrentRequest(BaseModel):
    """Hold current camera indefinitely request."""
    reason: Optional[str] = None


class LockCurrentRequest(BaseModel):
    """Lock current camera for duration request."""
    seconds: int = Field(..., ge=10, le=3600)
    reason: Optional[str] = None


class ReleaseLockRequest(BaseModel):
    """Release camera lock request."""
    reason: Optional[str] = None


class PanicCutRequest(BaseModel):
    """Panic cut request."""
    reason: Optional[str] = None


class ReconnectATEMRequest(BaseModel):
    """Reconnect to ATEM device request."""
    reason: Optional[str] = None


# ============================================================================
# Settings Update Schemas
# ============================================================================

class ChangeATEMIPRequest(BaseModel):
    """Change ATEM device IP request."""
    host: str = Field(..., min_length=7, max_length=255)
    port: int = Field(21124, ge=1024, le=65535)


class ChangeTransitionModeRequest(BaseModel):
    """Change transition mode request."""
    mode: str = Field(..., regex="^(cut|mix)$")


class ChangeMixDurationRequest(BaseModel):
    """Change mix transition duration request."""
    duration_ms: int = Field(..., ge=1, le=5000)


class ChangeInputEnabledRequest(BaseModel):
    """Enable/disable input for auto mode request."""
    input_index: int = Field(..., ge=1, le=32)
    enabled: bool


class SetSafeCameraRequest(BaseModel):
    """Set safe camera fallback request."""
    input_index: int = Field(..., ge=1, le=32)


class SetSwitchModeRequest(BaseModel):
    """Set switching mode request."""
    mode: str = Field(..., regex="^(pure_random|balanced_random|weighted_random|round_robin_random)$")


class SetCameraWeightRequest(BaseModel):
    """Set per-camera weight for weighted mode request."""
    input_index: int = Field(..., ge=1, le=32)
    weight: float = Field(..., ge=0.1, le=10.0)


class AdjustCooldownRequest(BaseModel):
    """Adjust cooldown settings request."""
    cooldown_seconds: float = Field(..., ge=0.0, le=300.0)


class IntervalEntry(BaseModel):
    """Interval pool entry."""
    interval_seconds: float = Field(..., ge=1.0, le=3600.0)
    name: Optional[str] = None


class AddIntervalRequest(BaseModel):
    """Add custom interval to pool request."""
    interval_seconds: float = Field(..., ge=1.0, le=3600.0)
    name: Optional[str] = None


class RemoveIntervalRequest(BaseModel):
    """Remove custom interval from pool request."""
    interval_seconds: float


class EnableIntervalRequest(BaseModel):
    """Enable interval in active pool request."""
    interval_seconds: float


class DisableIntervalRequest(BaseModel):
    """Disable interval in active pool request."""
    interval_seconds: float


# ============================================================================
# Preset Schemas
# ============================================================================

class PresetRequest(BaseModel):
    """Preset creation/save request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    program_input: int = Field(..., ge=1, le=32)
    preview_input: int = Field(..., ge=1, le=32)
    transition_mode: str = Field("cut", regex="^(cut|mix)$")
    transition_duration_ms: int = Field(300, ge=1, le=5000)
    enabled_inputs: Optional[List[int]] = None
    switch_mode: Optional[str] = None
    safe_camera: Optional[int] = None
    weights: Optional[Dict[int, float]] = None


class PresetResponse(BaseModel):
    """Preset response."""
    id: int
    name: str
    description: Optional[str]
    program_input: int
    preview_input: int
    transition_mode: str
    transition_duration_ms: int
    enabled_inputs: Optional[List[int]]
    switch_mode: Optional[str]
    safe_camera: Optional[int]
    weights: Optional[Dict[int, float]]
    created_at: datetime
    updated_at: datetime


class LoadPresetRequest(BaseModel):
    """Load preset request."""
    preset_id: int


# ============================================================================
# State and Status Schemas
# ============================================================================

class InputSourceSignalResponse(BaseModel):
    """Input source signal state."""
    input_index: int
    has_signal: bool
    signal_state: str  # 'none', 'program', 'preview', 'program_and_preview'


class SwitcherStateResponse(BaseModel):
    """Switcher state response."""
    program_input: int
    preview_input: int
    transition_mode: str
    transition_duration_ms: int
    is_transitioning: bool
    input_signals: Dict[int, InputSourceSignalResponse]
    live_stream_active: bool
    recording_active: bool


class ATEMCapabilitiesResponse(BaseModel):
    """ATEM device capabilities."""
    supports_transition_modes: bool
    supports_mix_transition: bool
    supports_dip_transition: bool
    supports_wipe_transition: bool
    supports_stinger_transition: bool
    max_mix_duration_ms: int
    min_mix_duration_ms: int
    supports_supersource: bool
    supports_streaming: bool
    supports_live_stream: bool


class ATEMStatusResponse(BaseModel):
    """ATEM device status response."""
    model: Optional[str]
    state: str
    firmware_version: Optional[str]
    uptime_seconds: int
    inputs_count: int
    outputs_count: int
    aux_outputs_count: int
    capabilities: ATEMCapabilitiesResponse
    last_error: Optional[str]
    connection_attempts: int


class EngineStateResponse(BaseModel):
    """Switching engine state response."""
    state: str  # IDLE, READY, RUNNING, PAUSED, LOCKED, RECONNECTING, ERROR
    enabled: bool
    current_input: int
    next_input: Optional[int]
    countdown_seconds: Optional[float]
    hold_duration_seconds: Optional[float]
    switch_mode: str
    safe_camera: int
    cooldown_seconds: float
    input_states: Dict[int, dict]  # Detailed per-input state


class RuntimeStateResponse(BaseModel):
    """Complete runtime state response."""
    atem_status: ATEMStatusResponse
    switcher_state: SwitcherStateResponse
    engine_state: EngineStateResponse
    session_active: bool
    session_name: Optional[str]
    session_started_at: Optional[datetime]
    session_switches_count: int


# ============================================================================
# Statistics and Log Schemas
# ============================================================================

class CameraStatisticsResponse(BaseModel):
    """Per-camera statistics."""
    input_index: int
    switch_count: int
    total_program_seconds: float
    last_switched_at: Optional[datetime]
    average_hold_seconds: Optional[float]
    usage_percentage: float


class SessionStatisticsResponse(BaseModel):
    """Session statistics."""
    total_switches: int
    total_duration_seconds: float
    average_hold_seconds: Optional[float]
    camera_stats: List[CameraStatisticsResponse]


class SwitchingEventResponse(BaseModel):
    """Switching event log entry."""
    id: int
    event_type: str
    from_input: Optional[int]
    to_input: Optional[int]
    reason: Optional[str]
    hold_duration_seconds: Optional[float]
    is_success: bool
    error_message: Optional[str]
    created_at: datetime


class LogQueryResponse(BaseModel):
    """Log query response."""
    events: List[SwitchingEventResponse]
    total_count: int
    limit: int
    offset: int


# ============================================================================
# Control Response Schemas
# ============================================================================

class OperationResponse(BaseModel):
    """Generic operation response."""
    success: bool
    message: str
    operation: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: str
    timestamp: datetime
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    version: str
    uptime_seconds: float
    atem_connected: bool
    database_ok: bool
    timestamp: datetime
