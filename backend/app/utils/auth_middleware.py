"""
JWT Authentication Middleware — Token verification and user extraction.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import get_settings

security = HTTPBearer()
settings = get_settings()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency that extracts and validates the JWT token
    from the Authorization header. Returns the decoded user payload.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return {
            "email": email,
            "name": payload.get("name", ""),
            "role": payload.get("role", "admin"),
        }
    except JWTError:
        raise credentials_exception
