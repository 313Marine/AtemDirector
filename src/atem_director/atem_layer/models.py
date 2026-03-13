"""ATEM device models and types."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


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
    ERROR = "error"


class ATEMStatus(BaseModel):
    """ATEM device status."""
    model: Optional[MixerModel] = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    firmware_version: Optional[str] = None
    uptime_seconds: int = 0
    inputs_count: int = 0
    outputs_count: int = 0
    aux_outputs_count: int = 0
    has_video_mix_effect: bool = False
    has_supersource: bool = False


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
    transition_position: int = 0
    transition_duration: int = 30
    is_transitioning: bool = False
