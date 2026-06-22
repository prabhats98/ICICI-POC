"""
Auth API — Login, profile, and logout endpoints.
Single pre-configured user for CloudGuard platform access.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.utils.auth_middleware import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pre-configured admin user
_ADMIN_USER = {
    "email": "admin@krelixir.com",
    "name": "Admin",
    "role": "admin",
    "password_hash": pwd_context.hash("CloudGuard@2026!"),
}


# ---------- Schemas ----------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    email: str
    name: str
    role: str


# ---------- Helpers ----------

def _create_access_token(data: dict) -> str:
    """Create a signed JWT with expiry."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    to_encode = {**data, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ---------- Routes ----------

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate with email and password, return JWT."""
    if body.email.lower() != _ADMIN_USER["email"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not pwd_context.verify(body.password, _ADMIN_USER["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = _create_access_token({
        "sub": _ADMIN_USER["email"],
        "name": _ADMIN_USER["name"],
        "role": _ADMIN_USER["role"],
    })

    return LoginResponse(
        access_token=token,
        user={
            "email": _ADMIN_USER["email"],
            "name": _ADMIN_USER["name"],
            "role": _ADMIN_USER["role"],
        },
    )


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse(**user)


@router.post("/logout")
async def logout():
    """Client-side logout (token removal). Server acknowledges."""
    return {"detail": "Logged out successfully"}
