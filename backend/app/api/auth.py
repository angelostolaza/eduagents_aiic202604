from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response, status
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.config import get_settings
from app.ids import make_id
from app.models import UserAccount, UserTier
from app.schemas.auth import LoginRequest, RegisterRequest, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def _create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.app_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: DB) -> TokenOut:
    existing = await db.execute(
        select(UserAccount).where(UserAccount.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_taken", "message": "An account with this email already exists."},
        )

    user = UserAccount(
        id=make_id("user"),
        email=body.email,
        hashed_password=_hash_password(body.password),
        tier=UserTier.public.value,
        daily_cap=settings.whitelisted_daily_cap,
        weekly_cap=settings.whitelisted_weekly_cap,
    )
    db.add(user)
    await db.flush()

    token = _create_access_token(user.id)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest, response: Response, db: DB) -> TokenOut:
    result = await db.execute(
        select(UserAccount).where(UserAccount.email == body.email)
    )
    user = result.scalar_one_or_none()

    # Constant-time comparison prevents user enumeration
    dummy_hash = "$2b$12$notavalidhash000000000000000000000000000000000000"
    if user is None:
        _verify_password(body.password, dummy_hash)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid email or password."},
        )

    if not _verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid email or password."},
        )

    if user.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_frozen", "message": "This account has been suspended."},
        )

    token = _create_access_token(user.id)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return TokenOut(access_token=token)


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)
