"""Main application entrypoint."""
import uvicorn
from atem_director.config import get_settings
from atem_director.app import create_app


def main() -> None:
    """Run the application."""
    settings = get_settings()
    app = create_app(settings)
    
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers,
        log_level=settings.api.log_level,
    )


if __name__ == "__main__":
    main()
