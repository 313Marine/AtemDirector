"""ATEM Director CLI entrypoint."""
import sys
from atem_director.config import get_settings
from atem_director.app import create_app
from atem_director.logging import configure_logging


def main() -> None:
    """Main CLI entrypoint."""
    settings = get_settings()
    configure_logging(settings.api.log_level)
    
    app = create_app(settings)
    
    # Import uvicorn here to avoid hard dependency
    import uvicorn
    
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
