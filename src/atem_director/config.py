"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Literal


class ATEMConfig(BaseSettings):
    """ATEM device configuration."""
    host: str = "192.168.1.100"
    port: int = 21124
    connection_timeout: float = 5.0
    reconnect_attempts: int = 3
    reconnect_delay: float = 2.0


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    url: str = "postgresql+asyncpg://user:password@localhost/atem_director"
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 40
    pool_pre_ping: bool = True
    migration_auto: bool = False


class APIConfig(BaseSettings):
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    cors_origins: list[str] = ["*"]


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class Settings(BaseSettings):
    """Application settings."""
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    
    atem: ATEMConfig = ATEMConfig()
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    auth: AuthConfig = AuthConfig()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
