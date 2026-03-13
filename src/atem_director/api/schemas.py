"""API request/response schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


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


class PresetRequest(BaseModel):
    """Preset creation/update request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    program_input: int = Field(..., ge=0)
    preview_input: int = Field(..., ge=0)
    transition_duration: int = Field(30, ge=1, le=3000)


class PresetResponse(BaseModel):
    """Preset response."""
    name: str
    description: Optional[str]
    program_input: int
    preview_input: int
    transition_duration: int


class SwitcherStateResponse(BaseModel):
    """Switcher state response."""
    program_input: int
    preview_input: int
    transition_position: int
    transition_duration: int
    is_transitioning: bool


class ATEMStatusResponse(BaseModel):
    """ATEM device status response."""
    model: Optional[str]
    state: str
    firmware_version: Optional[str]
    uptime_seconds: int
    is_connected: bool
