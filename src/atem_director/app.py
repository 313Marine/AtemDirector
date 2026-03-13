"""Application factory and bootstrap."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atem_director.config import Settings
from atem_director.logging import configure_logging, get_logger
from atem_director.persistence.database import init_db, close_db
from atem_director.api import router as api_router
from atem_director.atem_layer.manager import ATEMManager

logger = get_logger(__name__)


async def startup(app: FastAPI, settings: Settings) -> None:
    """Application startup handler."""
    logger.info("Starting ATEM Director application", env=settings.env)
    
    # Initialize database
    await init_db(settings.database.url)
    logger.info("Database initialized")
    
    # Initialize ATEM manager
    atem_manager = ATEMManager(settings.atem)
    app.state.atem_manager = atem_manager
    await atem_manager.connect()
    logger.info("ATEM connection established", host=settings.atem.host)


async def shutdown(app: FastAPI) -> None:
    """Application shutdown handler."""
    logger.info("Shutting down ATEM Director application")
    
    # Close ATEM connection
    atem_manager: ATEMManager = app.state.atem_manager
    await atem_manager.disconnect()
    logger.info("ATEM connection closed")
    
    # Close database
    await close_db()
    logger.info("Database closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    settings: Settings = app.state.settings
    await startup(app, settings)
    yield
    await shutdown(app)


def create_app(settings: Settings) -> FastAPI:
    """Create and configure FastAPI application."""
    configure_logging(settings.api.log_level)
    
    app = FastAPI(
        title="ATEM Director",
        description="Control and orchestrate ATEM video switchers",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    app.state.settings = settings
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(api_router.router, prefix="/api/v1")
    
    logger.info("FastAPI application created", debug=settings.debug)
    
    return app
