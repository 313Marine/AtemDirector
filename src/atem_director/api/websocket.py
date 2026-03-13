"""WebSocket endpoints for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio
import json
from typing import Set
from datetime import datetime

from atem_director.logging import get_logger
from atem_director.services.runtime import ApplicationOrchestrator

logger = get_logger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()


async def get_orchestrator_from_app(app):
    """Get orchestrator from FastAPI app state."""
    orchestrator = getattr(app.state, 'orchestrator', None)
    if not orchestrator:
        raise RuntimeError("Orchestrator not initialized")
    return orchestrator


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.
    
    Publishes:
    - Connection state changes
    - Countdown updates
    - Switch events
    - Input signal changes
    - Lock/hold status
    - Warnings and errors
    """
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        logger.info("WebSocket client connected")
        
        # Get orchestrator
        orchestrator = await get_orchestrator_from_app(websocket.app)
        
        # Send initial state
        await send_initial_state(websocket, orchestrator)
        
        # Listen for client messages and publish updates
        while True:
            try:
                # Check for incoming messages (allows client to close connection)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                
                # Parse and handle client command if needed
                message = json.loads(data)
                logger.debug("WebSocket message received", message=message)
                
            except asyncio.TimeoutError:
                # No message received, continue to publish updates
                pass
            
            # Publish current state updates
            await publish_updates(websocket, orchestrator)
            
            await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        active_connections.discard(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        active_connections.discard(websocket)


async def send_initial_state(websocket: WebSocket, orchestrator: ApplicationOrchestrator) -> None:
    """Send initial state to newly connected client."""
    try:
        state = await orchestrator.get_current_state()
        
        message = {
            "type": "initial_state",
            "timestamp": datetime.now().isoformat(),
            "data": state,
        }
        
        await websocket.send_json(message)
        logger.debug("Sent initial state to WebSocket client")
        
    except Exception as e:
        logger.error("Failed to send initial state", error=str(e))


async def publish_updates(websocket: WebSocket, orchestrator: ApplicationOrchestrator) -> None:
    """Publish state updates to client."""
    try:
        # Get current state
        state = await orchestrator.get_current_state()
        
        # Prepare update message
        message = {
            "type": "state_update",
            "timestamp": datetime.now().isoformat(),
            "atem_status": state.get("atem_status"),
            "switcher_state": state.get("switcher_state"),
            "engine_state": state.get("engine_state"),
            "session_active": state.get("session_active"),
            "session_switches_count": state.get("session_switches_count"),
        }
        
        await websocket.send_json(message)
        
    except Exception as e:
        logger.error("Failed to publish updates", error=str(e))


async def broadcast_update(update_type: str, data: dict) -> None:
    """Broadcast update to all connected clients.
    
    Args:
        update_type: Type of update (connection, switch, lock, warning, etc.)
        data: Update data
    """
    if not active_connections:
        return
    
    message = {
        "type": update_type,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }
    
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.warning("Failed to send WebSocket message", error=str(e))
            disconnected.add(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        active_connections.discard(connection)


async def broadcast_connection_change(state: str) -> None:
    """Broadcast connection state change."""
    await broadcast_update("connection_state", {"state": state})


async def broadcast_switch_event(
    from_input: int,
    to_input: int,
    reason: str = None,
    hold_duration: float = None,
) -> None:
    """Broadcast switching event."""
    await broadcast_update("switch_event", {
        "from_input": from_input,
        "to_input": to_input,
        "reason": reason,
        "hold_duration_seconds": hold_duration,
    })


async def broadcast_countdown_update(
    remaining_seconds: float,
    next_input: int = None,
) -> None:
    """Broadcast countdown update."""
    await broadcast_update("countdown_update", {
        "remaining_seconds": remaining_seconds,
        "next_input": next_input,
    })


async def broadcast_lock_status(
    locked: bool,
    current_input: int = None,
    expires_in_seconds: float = None,
) -> None:
    """Broadcast lock status change."""
    await broadcast_update("lock_status", {
        "locked": locked,
        "current_input": current_input,
        "expires_in_seconds": expires_in_seconds,
    })


async def broadcast_signal_change(
    input_index: int,
    has_signal: bool,
) -> None:
    """Broadcast input signal change."""
    await broadcast_update("signal_change", {
        "input_index": input_index,
        "has_signal": has_signal,
    })


async def broadcast_warning(message: str, level: str = "warning") -> None:
    """Broadcast warning message."""
    await broadcast_update("warning", {
        "message": message,
        "level": level,
    })


async def broadcast_error(message: str) -> None:
    """Broadcast error message."""
    await broadcast_update("error", {
        "message": message,
    })
