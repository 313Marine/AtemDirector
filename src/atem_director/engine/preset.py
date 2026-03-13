"""Preset management engine."""
from typing import Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PresetConfig:
    """Preset configuration."""
    program_input: int
    preview_input: int
    transition_duration: int = 30
    metadata: dict[str, Any] | None = None


class PresetManager:
    """Manages switching presets."""
    
    def __init__(self) -> None:
        """Initialize preset manager."""
        self.presets: dict[str, PresetConfig] = {}
        self.active_preset: Optional[str] = None
    
    def create_preset(
        self,
        name: str,
        config: PresetConfig,
    ) -> None:
        """Create a new preset.
        
        Args:
            name: Preset name
            config: Preset configuration
        """
        if name in self.presets:
            raise ValueError(f"Preset '{name}' already exists")
        
        self.presets[name] = config
    
    def delete_preset(self, name: str) -> None:
        """Delete a preset.
        
        Args:
            name: Preset name
        """
        if name not in self.presets:
            raise ValueError(f"Preset '{name}' not found")
        
        del self.presets[name]
        
        if self.active_preset == name:
            self.active_preset = None
    
    def update_preset(
        self,
        name: str,
        config: PresetConfig,
    ) -> None:
        """Update an existing preset.
        
        Args:
            name: Preset name
            config: New preset configuration
        """
        if name not in self.presets:
            raise ValueError(f"Preset '{name}' not found")
        
        self.presets[name] = config
    
    def get_preset(self, name: str) -> Optional[PresetConfig]:
        """Get preset configuration.
        
        Args:
            name: Preset name
            
        Returns:
            Preset configuration or None if not found
        """
        return self.presets.get(name)
    
    def list_presets(self) -> list[str]:
        """List all preset names."""
        return list(self.presets.keys())
    
    def activate_preset(self, name: str) -> PresetConfig:
        """Activate a preset.
        
        Args:
            name: Preset name
            
        Returns:
            Activated preset configuration
        """
        if name not in self.presets:
            raise ValueError(f"Preset '{name}' not found")
        
        self.active_preset = name
        return self.presets[name]
    
    def get_active_preset(self) -> Optional[PresetConfig]:
        """Get currently active preset configuration."""
        if self.active_preset is None:
            return None
        
        return self.presets.get(self.active_preset)
