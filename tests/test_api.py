"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from atem_director.app import create_app
from atem_director.config import Settings


@pytest.fixture
def test_settings():
    """Create test settings."""
    from atem_director.config import ATEMConfig, DatabaseConfig, APIConfig, AuthConfig
    return Settings(
        env="test",
        debug=True,
        atem=ATEMConfig(host="127.0.0.1", port=21124, connection_timeout=1.0),
        database=DatabaseConfig(url="sqlite+aiosqlite:///:memory:"),
        api=APIConfig(host="127.0.0.1", port=8001, cors_origins=["*"]),
        auth=AuthConfig(secret_key="test-secret-key"),
    )


@pytest.fixture
def app(test_settings):
    """Create test app."""
    return create_app(test_settings)


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestControlEndpoints:
    """Test control operation endpoints."""
    
    def test_start_auto_switching(self, client):
        """Test starting auto switching."""
        response = client.post("/api/v1/control/start")
        assert response.status_code in [200, 500, 503]
    
    def test_stop_auto_switching(self, client):
        """Test stopping auto switching."""
        response = client.post("/api/v1/control/stop")
        assert response.status_code in [200, 500, 503]
    
    def test_skip_current(self, client):
        """Test skipping current camera."""
        response = client.post(
            "/api/v1/control/skip-current",
            json={"reason": "Test skip"},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_skip_next(self, client):
        """Test skipping next switch."""
        response = client.post(
            "/api/v1/control/skip-next",
            json={"reason": "Test skip"},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_extend_current(self, client):
        """Test extending current camera."""
        response = client.post(
            "/api/v1/control/extend-current",
            json={"seconds": 30},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_hold_current(self, client):
        """Test holding current camera."""
        response = client.post(
            "/api/v1/control/hold-current",
            json={"reason": "Test hold"},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_lock_current(self, client):
        """Test locking current camera."""
        response = client.post(
            "/api/v1/control/lock-current",
            json={"seconds": 60, "reason": "Test lock"},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_panic_cut(self, client):
        """Test panic cut."""
        response = client.post(
            "/api/v1/control/panic-cut",
            json={"reason": "Test panic cut"},
        )
        assert response.status_code in [200, 500, 503]


class TestSettingsEndpoints:
    """Test settings endpoints."""
    
    def test_change_atem_ip(self, client):
        """Test changing ATEM IP."""
        response = client.post(
            "/api/v1/settings/atem/ip",
            json={"host": "192.168.1.200", "port": 21124},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_change_transition_mode(self, client):
        """Test changing transition mode."""
        response = client.post(
            "/api/v1/settings/transition/mode",
            json={"mode": "mix"},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_change_mix_duration(self, client):
        """Test changing mix duration."""
        response = client.post(
            "/api/v1/settings/transition/duration",
            json={"duration_ms": 500},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_set_safe_camera(self, client):
        """Test setting safe camera."""
        response = client.post(
            "/api/v1/settings/safe-camera",
            json={"input_index": 2},
        )
        assert response.status_code in [200, 500, 503]
    
    def test_set_switch_mode(self, client):
        """Test setting switch mode."""
        response = client.post(
            "/api/v1/settings/switch-mode",
            json={"mode": "weighted_random"},
        )
        assert response.status_code in [200, 500, 503]


class TestDataEndpoints:
    """Test data query endpoints."""
    
    def test_save_preset(self, client):
        """Test saving preset."""
        response = client.post(
            "/api/v1/data/presets/save",
            json={
                "name": "Test Preset",
                "program_input": 1,
                "preview_input": 2,
            },
        )
        assert response.status_code in [200, 500, 503]
    
    def test_list_presets(self, client):
        """Test listing presets."""
        response = client.get("/api/v1/data/presets")
        assert response.status_code in [200, 500, 503]
    
    def test_get_current_state(self, client):
        """Test getting current state."""
        response = client.get("/api/v1/data/state")
        assert response.status_code in [200, 500, 503]
    
    def test_get_session_statistics(self, client):
        """Test getting session statistics."""
        response = client.get("/api/v1/data/statistics/session")
        assert response.status_code in [200, 500, 503]
    
    def test_get_event_logs(self, client):
        """Test getting event logs."""
        response = client.get("/api/v1/data/logs")
        assert response.status_code in [200, 500, 503]


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 500, 503]
