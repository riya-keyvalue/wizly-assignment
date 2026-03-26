from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError, TokenExpiredError

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _build_token(subject: str, token_type: str, lifetime_minutes: int) -> str:
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(minutes=lifetime_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "jti": jti,
        "type": token_type,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    return _build_token(subject, "access", settings.jwt_access_token_lifetime)


def create_refresh_token(subject: str) -> str:
    return _build_token(subject, "refresh", settings.jwt_refresh_token_lifetime)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        msg = str(exc)
        if "expired" in msg.lower():
            raise TokenExpiredError() from exc
        raise InvalidCredentialsError() from exc
    return payload
