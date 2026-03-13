"""Test fixtures."""
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from atem_director.config import Settings, ATEMConfig, DatabaseConfig, APIConfig, AuthConfig
from atem_director.persistence.models import Base
from atem_director.persistence.database import get_db_session
from atem_director.atem_layer.manager import ATEMManager
from atem_director.engine.preset import PresetManager
from atem_director.services.orchestrator import SwitchingOrchestrator


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        env="testing",
        debug=True,
        atem=ATEMConfig(host="127.0.0.1", connection_timeout=1.0),
        database=DatabaseConfig(url="sqlite+aiosqlite:///:memory:"),
        api=APIConfig(host="127.0.0.1", port=8001),
        auth=AuthConfig(secret_key="test-secret-key"),
    )


@pytest.fixture
async def test_db(settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    engine = create_async_engine(settings.database.url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def atem_manager(settings: Settings) -> ATEMManager:
    """Create ATEM manager instance."""
    return ATEMManager(settings.atem)


@pytest.fixture
def preset_manager() -> PresetManager:
    """Create preset manager instance."""
    return PresetManager()


@pytest.fixture
def switching_orchestrator(
    atem_manager: ATEMManager,
    preset_manager: PresetManager,
) -> SwitchingOrchestrator:
    """Create switching orchestrator instance."""
    return SwitchingOrchestrator(atem_manager, preset_manager)
