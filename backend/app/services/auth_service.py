from __future__ import annotations

import logging
import uuid as _uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError, TokenBlacklistedError, UserAlreadyExistsError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserCreate

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise UserAlreadyExistsError()

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Registered new user: {user.email}")
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsError()

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    logger.info(f"User authenticated: {user.email}")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(db: AsyncSession, data: RefreshRequest) -> TokenResponse:
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise InvalidCredentialsError()

    jti: str = payload["jti"]
    result = await db.execute(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
    if result.scalar_one_or_none() is not None:
        raise TokenBlacklistedError()

    subject: str = payload["sub"]
    new_access_token = create_access_token(subject)
    new_refresh_token = create_refresh_token(subject)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


async def logout_user(db: AsyncSession, token: str) -> None:
    payload = decode_token(token)
    jti: str = payload["jti"]

    already = await db.execute(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
    if already.scalar_one_or_none() is not None:
        raise TokenBlacklistedError()

    exp: int = payload["exp"]
    expires_at = datetime.fromtimestamp(exp, tz=UTC)

    entry = TokenBlacklist(jti=jti, expires_at=expires_at)
    db.add(entry)
    await db.commit()
    logger.info(f"Token blacklisted: jti={jti}")


async def get_current_user(token: str, db: AsyncSession) -> User:
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise InvalidCredentialsError()

    jti: str = payload["jti"]
    result = await db.execute(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
    if result.scalar_one_or_none() is not None:
        raise TokenBlacklistedError()

    user_id = _uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsError()

    return user
