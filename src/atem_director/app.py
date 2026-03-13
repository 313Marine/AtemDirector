"""Application factory and bootstrap."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from atem_director.config import Settings
from atem_director.logging import configure_logging, get_logger
from atem_director.persistence.database import init_db, close_db
from atem_director.persistence.storage import StorageManager
from atem_director.atem_layer.manager import ATEMManager
from atem_director.engine.switching import SwitchingEngine
from atem_director.services.runtime import ApplicationOrchestrator
from atem_director.api import router as api_router
from atem_director.api import dashboard

logger = get_logger(__name__)


async def startup(app: FastAPI, settings: Settings) -> None:
    """Application startup handler."""
    logger.info("Starting ATEM Director application", env=settings.env)
    
    # Initialize database
    await init_db(settings.database.url)
    logger.info("Database initialized")
    
    # Initialize storage manager
    storage_manager = StorageManager()
    app.state.storage_manager = storage_manager
    logger.info("Storage manager initialized")
    
    # Initialize ATEM manager
    atem_manager = ATEMManager(settings.atem)
    app.state.atem_manager = atem_manager
    await atem_manager.connect()
    logger.info("ATEM connection established", host=settings.atem.host)
    
    # Initialize switching engine
    switching_engine = SwitchingEngine()
    app.state.switching_engine = switching_engine
    logger.info("Switching engine initialized")
    
    # Initialize orchestrator
    orchestrator = ApplicationOrchestrator(
        atem_manager=atem_manager,
        switching_engine=switching_engine,
        storage_manager=storage_manager,
        settings=settings,
    )
    app.state.orchestrator = orchestrator
    await orchestrator.initialize()
    logger.info("Application orchestrator initialized")


async def shutdown(app: FastAPI) -> None:
    """Application shutdown handler."""
    logger.info("Shutting down ATEM Director application")
    
    # Shutdown orchestrator
    orchestrator: ApplicationOrchestrator = app.state.orchestrator
    await orchestrator.shutdown()
    logger.info("Orchestrator shut down")
    
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
    
    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "../../static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Include dashboard route
    app.include_router(dashboard.router, tags=["dashboard"])
    
    # Include API routers
    app.include_router(api_router.router, prefix="/api/v1")
    
    logger.info("FastAPI application created", debug=settings.debug)
    
    return app
