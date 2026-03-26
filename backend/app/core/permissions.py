from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import InactiveUserError
from app.models.user import User
from app.services.auth_service import get_current_user

_bearer = HTTPBearer()


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await get_current_user(token=credentials.credentials, db=db)
    if not user.is_active:
        raise InactiveUserError()
    return user
