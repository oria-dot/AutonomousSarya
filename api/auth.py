"""
Authentication module for SARYA API.
Provides JWT-based authentication and authorization.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from core.config import config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auth")

# OAuth2 password bearer scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scopes={
        "admin": "Full administrative access",
        "read": "Read-only access",
        "write": "Write access",
        "clone": "Clone management",
        "plugin": "Plugin management",
        "metrics": "Metrics access",
        "reflex": "Reflex system access",
    },
)

class Token(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str
    expires_at: datetime
    scopes: list

class TokenData(BaseModel):
    """Schema for token data."""
    username: Optional[str] = None
    scopes: list = []

class User(BaseModel):
    """Schema for user data."""
    username: str
    disabled: bool = False
    scopes: list = []

# Sample user database - In a real application, this would be in a database
# For demonstration purposes only
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
        "scopes": ["admin", "read", "write", "clone", "plugin", "metrics", "reflex"],
    },
    "user": {
        "username": "user",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
        "scopes": ["read", "clone"],
    },
}

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default expiration: 1 hour
        expire = datetime.utcnow() + timedelta(hours=1)
    
    to_encode.update({"exp": expire})
    
    # Get JWT secret and algorithm from config
    secret_key = config_manager.get("api.jwt_secret", "insecure_default_secret")
    algorithm = config_manager.get("api.jwt_algorithm", "HS256")
    
    # Create and return token
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if the password matches the hash
    """
    from werkzeug.security import check_password_hash
    return check_password_hash(hashed_password, plain_password)

def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        User object if authentication was successful, None otherwise
    """
    if username not in USERS_DB:
        return None
    
    user_dict = USERS_DB[username]
    
    # Check password
    if not verify_password(password, user_dict["hashed_password"]):
        return None
    
    # Return user object
    return User(
        username=user_dict["username"],
        disabled=user_dict["disabled"],
        scopes=user_dict["scopes"],
    )

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Get the current user from a token.
    
    Args:
        security_scopes: Security scopes
        token: JWT token
        
    Returns:
        User object
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't have the required scopes
    """
    # Set up authentication error
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{" ".join(security_scopes.scopes)}"'
    else:
        authenticate_value = "Bearer"
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # Get JWT secret and algorithm from config
        secret_key = config_manager.get("api.jwt_secret", "insecure_default_secret")
        algorithm = config_manager.get("api.jwt_algorithm", "HS256")
        
        # Decode token
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Extract token data
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except (JWTError, ValidationError):
        logger.exception("Token validation error")
        raise credentials_exception
    
    # Get user from database
    if token_data.username not in USERS_DB:
        raise credentials_exception
    
    user_dict = USERS_DB[token_data.username]
    user = User(
        username=user_dict["username"],
        disabled=user_dict["disabled"],
        scopes=user_dict["scopes"],
    )
    
    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )
    
    # Check required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required scope: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return user

async def get_current_active_user(
    current_user: User = Security(get_current_user, scopes=["read"]),
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user
        
    Returns:
        User object
        
    Raises:
        HTTPException: If the user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )
    return current_user
