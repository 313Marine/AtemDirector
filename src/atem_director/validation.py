"""Comprehensive input validation utilities."""
from ipaddress import IPv4Address, AddressValueError
from typing import List, Set


def validate_ipv4_address(ip: str) -> bool:
    """Validate IPv4 address format."""
    try:
        IPv4Address(ip)
        return True
    except (AddressValueError, ValueError):
        return False


def validate_port(port: int) -> bool:
    """Validate port number."""
    return 1024 <= port <= 65535


def validate_input_index(input_index: int, max_inputs: int = 32) -> bool:
    """Validate input index is within valid range."""
    return 1 <= input_index <= max_inputs


def validate_duration_ms(duration_ms: int, min_ms: int = 1, max_ms: int = 5000) -> bool:
    """Validate mix duration in milliseconds."""
    return min_ms <= duration_ms <= max_ms


def validate_seconds(seconds: float, min_sec: float = 0.0, max_sec: float = 600.0) -> bool:
    """Validate duration in seconds."""
    return min_sec <= seconds <= max_sec


def validate_enabled_inputs(enabled: List[int], total_inputs: int = 32) -> bool:
    """Validate enabled inputs list."""
    if not enabled or not isinstance(enabled, list):
        return False
    return all(validate_input_index(i, total_inputs) for i in enabled)


def validate_weights(weights: dict, enabled: List[int]) -> bool:
    """Validate camera weights are within valid range."""
    if not weights:
        return True
    for input_idx, weight in weights.items():
        if not isinstance(weight, (int, float)):
            return False
        if weight < 0.1 or weight > 10.0:
            return False
        if input_idx not in enabled:
            return False
    return True
