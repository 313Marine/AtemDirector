"""Authentication and user service."""
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt

from atem_director.config import get_settings
from atem_director.logging import get_logger

logger = get_logger(__name__)



class AuthService:
    """Authentication and user management service."""
    
    def __init__(self) -> None:
        """Initialize auth service."""
        self.settings = get_settings()
    
    def hash_password(self, password: str) -> str:
        """Hash a password.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token.
        
        Args:
            user_id: User ID
            expires_delta: Token expiration time delta
            
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=self.settings.auth.access_token_expire_minutes
            )
        
        expire = datetime.utcnow() + expires_delta
        to_encode = {"sub": str(user_id), "exp": expire}
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.auth.secret_key,
            algorithm=self.settings.auth.algorithm,
        )
        
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int) -> str:
        """Create JWT refresh token.
        
        Args:
            user_id: User ID
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(
            days=self.settings.auth.refresh_token_expire_days
        )
        to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.auth.secret_key,
            algorithm=self.settings.auth.algorithm,
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[int]:
        """Verify JWT token and extract user ID.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.auth.secret_key,
                algorithms=[self.settings.auth.algorithm],
            )
            user_id: int = int(payload.get("sub", 0))
            return user_id if user_id > 0 else None
            
        except JWTError:
            logger.warning("Invalid JWT token")
            return None
