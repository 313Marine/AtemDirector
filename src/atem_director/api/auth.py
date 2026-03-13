"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException, status

from atem_director.api.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
)
from atem_director.services.auth import AuthService
from atem_director.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
async def register(request: UserRegisterRequest) -> TokenResponse:
    """Register a new user.
    
    Args:
        request: Registration request
        
    Returns:
        Token response with access and refresh tokens
    """
    logger.info("User registration attempt", username=request.username)
    
    # In production, this would:
    # 1. Check if user already exists
    # 2. Hash password
    # 3. Store in database
    # 4. Create tokens
    
    hashed_password = auth_service.hash_password(request.password)
    user_id = 1  # Placeholder
    
    access_token = auth_service.create_access_token(user_id)
    refresh_token = auth_service.create_refresh_token(user_id)
    
    logger.info("User registered successfully", username=request.username)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest) -> TokenResponse:
    """Login user.
    
    Args:
        request: Login request
        
    Returns:
        Token response with access and refresh tokens
    """
    logger.info("User login attempt", username=request.username)
    
    # In production, this would:
    # 1. Find user in database
    # 2. Verify password
    # 3. Create tokens
    
    user_id = 1  # Placeholder
    
    access_token = auth_service.create_access_token(user_id)
    refresh_token = auth_service.create_refresh_token(user_id)
    
    logger.info("User logged in successfully", username=request.username)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str) -> TokenResponse:
    """Refresh access token.
    
    Args:
        refresh_token: Refresh token
        
    Returns:
        New token response
    """
    user_id = auth_service.verify_token(refresh_token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    access_token = auth_service.create_access_token(user_id)
    new_refresh_token = auth_service.create_refresh_token(user_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )
