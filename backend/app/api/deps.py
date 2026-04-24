"""FastAPI dependency helpers shared across routers."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import UserAccount, UserTier
from sqlalchemy import select

settings = get_settings()
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAccount:
    """Validate JWT (from Authorization header or httpOnly cookie) and return the user."""
    token: str | None = None

    # 1. Try Authorization: Bearer <token>
    if credentials:
        token = credentials.credentials

    # 2. Fall back to httpOnly cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "Authentication required."},
        )

    try:
        payload = jwt.decode(
            token,
            settings.app_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise JWTError("Missing subject")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Token is invalid or expired."},
        )

    result = await db.execute(select(UserAccount).where(UserAccount.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "user_not_found", "message": "User no longer exists."},
        )

    if user.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_frozen", "message": "This account has been suspended."},
        )

    return user


async def require_admin(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
) -> UserAccount:
    if current_user.tier != UserTier.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Admin access required."},
        )
    return current_user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]
AdminUser = Annotated[UserAccount, Depends(require_admin)]
DB = Annotated[AsyncSession, Depends(get_db)]
