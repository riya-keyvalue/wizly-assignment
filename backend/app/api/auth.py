from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import rate_limit
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserRead
from app.services.auth_service import authenticate_user, logout_user, refresh_access_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()

_register_rl = Depends(rate_limit(max_requests=10, window_seconds=60))
_login_rl = Depends(rate_limit(max_requests=20, window_seconds=60))


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _rl: None = _register_rl,
) -> dict[str, UserRead]:
    user: User = await register_user(db, data)
    return {"data": UserRead.model_validate(user)}


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _rl: None = _login_rl,
) -> dict[str, TokenResponse]:
    tokens: TokenResponse = await authenticate_user(db, data)
    return {"data": tokens}


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, TokenResponse]:
    tokens: TokenResponse = await refresh_access_token(db, data)
    return {"data": tokens}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await logout_user(db, credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
