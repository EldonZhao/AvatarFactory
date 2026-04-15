"""
Admin authentication routes for AvatarFactory.

Provides JWT-based authentication for the Admin dashboard.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

# Configuration from environment variables
ADMIN_USERNAME = os.getenv("AVATARFACTORY_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("AVATARFACTORY_ADMIN_PASSWORD")
JWT_SECRET = os.getenv("AVATARFACTORY_JWT_SECRET")

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Cookie settings
COOKIE_NAME = "admin_token"
COOKIE_MAX_AGE = JWT_EXPIRATION_HOURS * 60 * 60  # 24 hours in seconds
# Use secure cookies only in production (when HTTPS is available)
COOKIE_SECURE = os.getenv("AVATARFACTORY_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"


def _get_jwt_secret() -> str:
    """Get JWT secret, generating a warning if not configured."""
    if JWT_SECRET:
        return JWT_SECRET
    # For development only - generate a random secret
    # This will cause tokens to be invalid after restart
    if not hasattr(_get_jwt_secret, "_dev_secret"):
        _get_jwt_secret._dev_secret = secrets.token_hex(32)
        print(
            "WARNING: AVATARFACTORY_JWT_SECRET not set. "
            "Using random secret - tokens will be invalid after restart."
        )
    return _get_jwt_secret._dev_secret


def _get_admin_password() -> str:
    """Get admin password, with fallback for development."""
    if ADMIN_PASSWORD:
        return ADMIN_PASSWORD
    # For development only
    print(
        "WARNING: AVATARFACTORY_ADMIN_PASSWORD not set. "
        "Using default password 'admin123' - NOT FOR PRODUCTION!"
    )
    return "admin123"


def create_token(username: str) -> str:
    """Create a JWT token for the given username."""
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload if valid."""
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


class UserResponse(BaseModel):
    username: str


class VerifyResponse(BaseModel):
    valid: bool
    username: Optional[str] = None


# Router
router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """
    Authenticate user and return JWT token in HttpOnly cookie.
    """
    # Validate credentials
    if request.username != ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if request.password != _get_admin_password():
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Create JWT token
    token = create_token(request.username)

    # Set HttpOnly cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    return LoginResponse(
        success=True,
        message="Login successful",
        user={"username": request.username},
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Clear authentication cookie.
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    return {"success": True, "message": "Logged out successfully"}


@router.get("/verify", response_model=VerifyResponse)
async def verify(admin_token: Optional[str] = Cookie(None)):
    """
    Verify if the current token is valid.
    """
    if not admin_token:
        return VerifyResponse(valid=False)

    payload = verify_token(admin_token)
    if not payload:
        return VerifyResponse(valid=False)

    return VerifyResponse(valid=True, username=payload.get("sub"))


@router.get("/me", response_model=UserResponse)
async def get_current_user(admin_token: Optional[str] = Cookie(None)):
    """
    Get current authenticated user info.
    """
    if not admin_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(admin_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return UserResponse(username=payload.get("sub", ""))
