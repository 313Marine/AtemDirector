"""ATEM device models and types."""
from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field


class MixerModel(str, Enum):
    """ATEM mixer models."""
    PRODUCTION_4K = "ATEM Production 4K"
    PRODUCTION_STUDIO_4K = "ATEM Production Studio 4K"
    CONSTELLATION_8K = "ATEM Constellation 8K"
    MINI_EXTREME_ISO_12G = "ATEM Mini Extreme ISO 12G"


class ConnectionState(str, Enum):
    """Connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class TransitionMode(str, Enum):
    """Transition modes."""
    CUT = "cut"
    MIX = "mix"


class InputSignalState(str, Enum):
    """Input signal state."""
    NONE = "none"
    PROGRAM = "program"
    PREVIEW = "preview"
    PROGRAM_AND_PREVIEW = "program_and_preview"


class InputSourceSignal(BaseModel):
    """Input source signal information."""
    input_index: int
    has_signal: bool = False
    signal_state: InputSignalState = InputSignalState.NONE


class ATEMCapabilities(BaseModel):
    """ATEM device capabilities."""
    supports_transition_modes: bool = True
    supports_mix_transition: bool = True
    supports_dip_transition: bool = False
    supports_wipe_transition: bool = False
    supports_stinger_transition: bool = False
    max_mix_duration_ms: int = 5000
    min_mix_duration_ms: int = 1
    supports_supersource: bool = False
    supports_streaming: bool = False
    supports_live_stream: bool = False


class ATEMStatus(BaseModel):
    """ATEM device status."""
    model: Optional[MixerModel] = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    firmware_version: Optional[str] = None
    uptime_seconds: int = 0
    inputs_count: int = 0
    outputs_count: int = 0
    aux_outputs_count: int = 0
    capabilities: ATEMCapabilities = Field(default_factory=ATEMCapabilities)
    last_error: Optional[str] = None
    connection_attempts: int = 0


class InputSource(BaseModel):
    """Input source information."""
    index: int
    name: str
    availability: str
    short_name: str
    external_port_type: Optional[str] = None


class SwitcherState(BaseModel):
    """Current switcher state."""
    program_input: int = 0
    preview_input: int = 1
    transition_mode: TransitionMode = TransitionMode.CUT
    transition_position: int = 0
    transition_duration_ms: int = 300
    is_transitioning: bool = False
    input_signals: Dict[int, InputSourceSignal] = Field(default_factory=dict)
    live_stream_active: bool = False
    recording_active: bool = False
