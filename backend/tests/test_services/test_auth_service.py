from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError, TokenBlacklistedError, UserAlreadyExistsError
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import LoginRequest, RefreshRequest, UserCreate
from app.services.auth_service import (
    authenticate_user,
    get_current_user,
    logout_user,
    refresh_access_token,
    register_user,
)
from tests.factories import UserFactory


class TestRegisterUser:
    async def test_register_creates_user(self, db: AsyncSession) -> None:
        data = UserCreate(email="alice@example.com", password="password123")
        user = await register_user(db, data)

        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.hashed_password != "password123"
        assert user.is_active is True

    async def test_register_duplicate_raises(self, db: AsyncSession) -> None:
        data = UserCreate(email="bob@example.com", password="password123")
        await register_user(db, data)

        with pytest.raises(UserAlreadyExistsError):
            await register_user(db, data)


class TestAuthenticateUser:
    async def test_authenticate_success(self, db: AsyncSession) -> None:
        db.add(UserFactory.build(email="carol@example.com"))
        await db.commit()

        data = LoginRequest(email="carol@example.com", password="password123")
        tokens = await authenticate_user(db, data)

        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.token_type == "bearer"

    async def test_authenticate_wrong_password(self, db: AsyncSession) -> None:
        db.add(UserFactory.build(email="dave@example.com"))
        await db.commit()

        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(db, LoginRequest(email="dave@example.com", password="wrong"))

    async def test_authenticate_unknown_email(self, db: AsyncSession) -> None:
        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(db, LoginRequest(email="ghost@example.com", password="password123"))


class TestRefreshAccessToken:
    async def test_refresh_success(self, db: AsyncSession) -> None:
        db.add(UserFactory.build(email="eve@example.com"))
        await db.commit()

        user_data = UserCreate(email="frank@example.com", password="password123")
        user = await register_user(db, user_data)
        refresh_token = create_refresh_token(str(user.id))

        tokens = await refresh_access_token(db, RefreshRequest(refresh_token=refresh_token))

        assert tokens.access_token
        assert tokens.refresh_token

    async def test_refresh_with_access_token_raises(self, db: AsyncSession) -> None:
        user_data = UserCreate(email="grace@example.com", password="password123")
        user = await register_user(db, user_data)
        access_token = create_access_token(str(user.id))

        with pytest.raises(InvalidCredentialsError):
            await refresh_access_token(db, RefreshRequest(refresh_token=access_token))


class TestLogoutUser:
    async def test_logout_blacklists_jti(self, db: AsyncSession) -> None:
        user_data = UserCreate(email="henry@example.com", password="password123")
        user = await register_user(db, user_data)
        access_token = create_access_token(str(user.id))

        await logout_user(db, access_token)

        # Second logout should raise because JTI is already blacklisted
        with pytest.raises(TokenBlacklistedError):
            await logout_user(db, access_token)


class TestGetCurrentUser:
    async def test_get_current_user_success(self, db: AsyncSession) -> None:
        user_data = UserCreate(email="iris@example.com", password="password123")
        user = await register_user(db, user_data)
        access_token = create_access_token(str(user.id))

        fetched = await get_current_user(token=access_token, db=db)
        assert fetched.email == "iris@example.com"

    async def test_get_current_user_blacklisted_token(self, db: AsyncSession) -> None:
        user_data = UserCreate(email="jack@example.com", password="password123")
        user = await register_user(db, user_data)
        access_token = create_access_token(str(user.id))

        await logout_user(db, access_token)

        with pytest.raises(TokenBlacklistedError):
            await get_current_user(token=access_token, db=db)

    async def test_get_current_user_refresh_token_rejected(self, db: AsyncSession) -> None:
        user_data = UserCreate(email="kate@example.com", password="password123")
        user = await register_user(db, user_data)
        refresh_token = create_refresh_token(str(user.id))

        with pytest.raises(InvalidCredentialsError):
            await get_current_user(token=refresh_token, db=db)
