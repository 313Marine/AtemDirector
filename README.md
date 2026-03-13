# ATEM Director

Production-grade ATEM video switcher control and orchestration platform.

## Overview

ATEM Director provides a complete Python backend for controlling and managing ATEM video mixers. Features include:

- **Real-time Device Control**: Direct communication with ATEM mixers via TCP
- **Preset Management**: Create and execute switching presets
- **REST API**: FastAPI-based RESTful interface
- **Authentication**: JWT-based user authentication and authorization
- **Database Persistence**: PostgreSQL support for presets and user management
- **Structured Logging**: Production-grade logging with structlog

## Architecture

```
atem_director/
├── atem_layer/          # ATEM device layer (pyatem integration)
├── engine/              # Core switching engine (preset management)
├── persistence/         # Database models and session management
├── services/            # Business logic (auth, orchestration)
├── api/                 # REST API endpoints
├── config.py            # Configuration management
├── logging.py           # Logging setup
├── app.py               # FastAPI application factory
└── main.py              # Application entrypoint
```

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 13+ (for production)

### Setup

```bash
# Clone repository
git clone https://github.com/313Marine/AtemDirector.git
cd AtemDirector

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

Create `.env` file in project root:

```env
# ATEM Device
ATEM_HOST=192.168.1.100
ATEM_PORT=21124

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/atem_director

# API
API_HOST=0.0.0.0
API_PORT=8000

# Auth
AUTH_SECRET_KEY=your-secret-key-change-in-production
```

## Development Workflow

### Local Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run development server with auto-reload
python -m atem_director.main

# Or use make if available
make dev
```

The server will start at `http://localhost:8000`

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/atem_director

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/atem_director

# Import sorting
isort src/ tests/
```

## API Documentation

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user","email":"user@example.com","password":"securepass123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"securepass123"}'
```

### Switcher Control

```bash
# Get ATEM status
curl http://localhost:8000/api/v1/switcher/status

# Get switcher state
curl http://localhost:8000/api/v1/switcher/state

# Set program input
curl -X POST http://localhost:8000/api/v1/switcher/program/1

# Set preview input
curl -X POST http://localhost:8000/api/v1/switcher/preview/2

# Create preset
curl -X POST http://localhost:8000/api/v1/switcher/presets \
  -H "Content-Type: application/json" \
  -d '{"name":"preset1","program_input":1,"preview_input":2}'

# Execute preset
curl -X POST http://localhost:8000/api/v1/switcher/presets/preset1/execute
```

## Project Structure

### Key Components

- **ATEMManager** (`atem_layer/manager.py`): Handles device connection and communication
- **PresetManager** (`engine/preset.py`): Manages switching presets
- **AuthService** (`services/auth.py`): Handles JWT tokens and password hashing
- **SwitchingOrchestrator** (`services/orchestrator.py`): Coordinates switching operations
- **API Routers**: Health, authentication, and switcher control endpoints

### Database Models

- **User**: User accounts and authentication
- **Preset**: Switching preset configurations
- **Session**: User session tracking

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| ENV | development | Application environment |
| DEBUG | false | Enable debug mode |
| ATEM_HOST | 192.168.1.100 | ATEM device IP address |
| ATEM_PORT | 21124 | ATEM device port |
| DATABASE_URL | postgresql://... | Database connection URL |
| API_HOST | 0.0.0.0 | API server host |
| API_PORT | 8000 | API server port |
| AUTH_SECRET_KEY | (required) | JWT secret key |

## Common Tasks

### Adding a New API Endpoint

1. Define schema in `api/schemas.py`
2. Create endpoint function in appropriate router file
3. Add tests in `tests/` directory
4. Document in this README

### Adding a Database Migration

```bash
# Create migration (uses Alembic)
alembic revision --autogenerate -m "Add new table"

# Run migration
alembic upgrade head
```

### Extending ATEM Control

1. Add model in `atem_layer/models.py`
2. Implement in `atem_layer/manager.py`
3. Expose via API endpoints
4. Add tests

## Troubleshooting

### Connection Issues

- Verify ATEM device IP and port in `.env`
- Check network connectivity: `ping {ATEM_HOST}`
- Verify firewall allows TCP port 21124

### Database Connection

- Verify PostgreSQL is running
- Check DATABASE_URL format
- Test connection: `psql {DATABASE_URL}`

### API Not Responding

- Check logs: `tail -f logs/app.log`
- Verify API_HOST and API_PORT are correct
- Check for port conflicts: `lsof -i :{API_PORT}`

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please use the GitHub issues tracker.
