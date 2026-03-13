"""Unit tests for auth service."""
import pytest
from datetime import timedelta

from atem_director.services.auth import AuthService
from atem_director.config import AuthConfig


@pytest.fixture
def auth_service() -> AuthService:
    """Create auth service instance."""
    return AuthService()


def test_hash_password(auth_service: AuthService) -> None:
    """Test password hashing."""
    password = "test-password-123"
    hashed = auth_service.hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0


def test_verify_password(auth_service: AuthService) -> None:
    """Test password verification."""
    password = "test-password-123"
    hashed = auth_service.hash_password(password)
    
    assert auth_service.verify_password(password, hashed) is True
    assert auth_service.verify_password("wrong-password", hashed) is False


def test_create_access_token(auth_service: AuthService) -> None:
    """Test access token creation."""
    user_id = 1
    token = auth_service.create_access_token(user_id)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_token(auth_service: AuthService) -> None:
    """Test token verification."""
    user_id = 1
    token = auth_service.create_access_token(user_id)
    
    verified_id = auth_service.verify_token(token)
    
    assert verified_id == user_id


def test_verify_invalid_token(auth_service: AuthService) -> None:
    """Test invalid token verification."""
    verified_id = auth_service.verify_token("invalid-token")
    
    assert verified_id is None
