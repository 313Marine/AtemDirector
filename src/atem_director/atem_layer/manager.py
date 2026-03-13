"""ATEM connection and management."""
import asyncio
from typing import Optional, Any
from pyatem.connection import Connection
from pyatem.protocol import ProtocolHandler

from atem_director.config import ATEMConfig
from atem_director.logging import get_logger
from atem_director.atem_layer.models import ATEMStatus, ConnectionState, SwitcherState

logger = get_logger(__name__)


class ATEMManager:
    """Manages connection and communication with ATEM mixer."""
    
    def __init__(self, config: ATEMConfig) -> None:
        """Initialize ATEM manager.
        
        Args:
            config: ATEM device configuration
        """
        self.config = config
        self.connection: Optional[Connection] = None
        self.handler: Optional[ProtocolHandler] = None
        self._state = ATEMStatus()
        self._is_connected = False
        self._reconnect_task: Optional[asyncio.Task[Any]] = None
    
    async def connect(self) -> None:
        """Establish connection to ATEM device."""
        attempt = 0
        while attempt < self.config.reconnect_attempts:
            try:
                logger.info(
                    "Connecting to ATEM device",
                    host=self.config.host,
                    port=self.config.port,
                    attempt=attempt + 1
                )
                
                self.connection = Connection(
                    self.config.host,
                    self.config.port,
                )
                
                # Create protocol handler
                self.handler = ProtocolHandler(self.connection)
                
                # Attempt connection with timeout
                await asyncio.wait_for(
                    self._async_connect_handshake(),
                    timeout=self.config.connection_timeout
                )
                
                self._is_connected = True
                self._state.state = ConnectionState.CONNECTED
                logger.info("Successfully connected to ATEM device")
                return
                
            except asyncio.TimeoutError:
                logger.warning(
                    "Connection timeout",
                    attempt=attempt + 1,
                    max_attempts=self.config.reconnect_attempts
                )
                if self.connection:
                    self.connection.close()
                
            except Exception as e:
                logger.error(
                    "Connection error",
                    error=str(e),
                    attempt=attempt + 1,
                    max_attempts=self.config.reconnect_attempts
                )
                if self.connection:
                    self.connection.close()
            
            attempt += 1
            if attempt < self.config.reconnect_attempts:
                await asyncio.sleep(self.config.reconnect_delay)
        
        self._is_connected = False
        self._state.state = ConnectionState.ERROR
        logger.error("Failed to connect to ATEM device after all attempts")
    
    async def _async_connect_handshake(self) -> None:
        """Perform async connection handshake."""
        # This is a placeholder for the actual handshake logic
        # In production, this would interact with the pyatem library
        await asyncio.sleep(0.1)
    
    async def disconnect(self) -> None:
        """Close connection to ATEM device."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self.connection:
            self.connection.close()
        
        self._is_connected = False
        self._state.state = ConnectionState.DISCONNECTED
        logger.info("Disconnected from ATEM device")
    
    async def get_status(self) -> ATEMStatus:
        """Get current ATEM device status."""
        if not self._is_connected:
            return ATEMStatus(state=ConnectionState.DISCONNECTED)
        
        # In production, this would query real device status
        return self._state
    
    async def get_switcher_state(self) -> SwitcherState:
        """Get current switcher state."""
        if not self._is_connected:
            return SwitcherState()
        
        # In production, this would query real switcher state
        return SwitcherState()
    
    async def set_program_input(self, input_index: int) -> None:
        """Set program input.
        
        Args:
            input_index: Input source index
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to ATEM device")
        
        logger.info("Setting program input", input_index=input_index)
        # In production, this would send command to device
    
    async def set_preview_input(self, input_index: int) -> None:
        """Set preview input.
        
        Args:
            input_index: Input source index
        """
        if not self._is_connected:
            raise RuntimeError("Not connected to ATEM device")
        
        logger.info("Setting preview input", input_index=input_index)
        # In production, this would send command to device
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to ATEM device."""
        return self._is_connected
