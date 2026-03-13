"""Unit tests for preset manager."""
import pytest

from atem_director.engine.preset import PresetManager, PresetConfig


def test_create_preset(preset_manager: PresetManager) -> None:
    """Test preset creation."""
    preset_config = PresetConfig(program_input=1, preview_input=2)
    
    preset_manager.create_preset("test-preset", preset_config)
    
    assert "test-preset" in preset_manager.presets
    assert preset_manager.get_preset("test-preset") == preset_config


def test_create_duplicate_preset(preset_manager: PresetManager) -> None:
    """Test creating duplicate preset raises error."""
    preset_config = PresetConfig(program_input=1, preview_input=2)
    preset_manager.create_preset("test-preset", preset_config)
    
    with pytest.raises(ValueError, match="already exists"):
        preset_manager.create_preset("test-preset", preset_config)


def test_delete_preset(preset_manager: PresetManager) -> None:
    """Test preset deletion."""
    preset_config = PresetConfig(program_input=1, preview_input=2)
    preset_manager.create_preset("test-preset", preset_config)
    
    preset_manager.delete_preset("test-preset")
    
    assert "test-preset" not in preset_manager.presets


def test_list_presets(preset_manager: PresetManager) -> None:
    """Test listing presets."""
    preset_config1 = PresetConfig(program_input=1, preview_input=2)
    preset_config2 = PresetConfig(program_input=3, preview_input=4)
    
    preset_manager.create_preset("preset1", preset_config1)
    preset_manager.create_preset("preset2", preset_config2)
    
    presets = preset_manager.list_presets()
    
    assert len(presets) == 2
    assert "preset1" in presets
    assert "preset2" in presets


def test_activate_preset(preset_manager: PresetManager) -> None:
    """Test preset activation."""
    preset_config = PresetConfig(program_input=1, preview_input=2)
    preset_manager.create_preset("test-preset", preset_config)
    
    activated = preset_manager.activate_preset("test-preset")
    
    assert activated == preset_config
    assert preset_manager.active_preset == "test-preset"
