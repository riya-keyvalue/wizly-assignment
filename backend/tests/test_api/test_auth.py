from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from tests.factories import UserFactory

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
REFRESH_URL = "/auth/refresh"
LOGOUT_URL = "/auth/logout"


async def _create_user(db: AsyncSession, email: str = "alice@example.com", password: str = "password123") -> User:
    user: User = UserFactory.build(email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        response = await client.post(REGISTER_URL, json={"email": "new@example.com", "password": "password123"})

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["email"] == "new@example.com"
        assert "hashed_password" not in body["data"]
        assert "id" in body["data"]

    async def test_register_duplicate_email(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_user(db, email="dup@example.com")

        response = await client.post(REGISTER_URL, json={"email": "dup@example.com", "password": "password123"})

        assert response.status_code == 409

    async def test_register_short_password(self, client: AsyncClient) -> None:
        response = await client.post(REGISTER_URL, json={"email": "short@example.com", "password": "abc"})

        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        response = await client.post(REGISTER_URL, json={"email": "not-an-email", "password": "password123"})

        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_user(db, email="bob@example.com", password="password123")

        response = await client.post(LOGIN_URL, json={"email": "bob@example.com", "password": "password123"})

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"

    async def test_login_bad_password(self, client: AsyncClient, db: AsyncSession) -> None:
        await _create_user(db, email="carol@example.com")

        response = await client.post(LOGIN_URL, json={"email": "carol@example.com", "password": "wrongpassword"})

        assert response.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient) -> None:
        response = await client.post(LOGIN_URL, json={"email": "ghost@example.com", "password": "password123"})

        assert response.status_code == 401


class TestRefresh:
    async def test_refresh_token(self, client: AsyncClient, db: AsyncSession) -> None:
        user = await _create_user(db, email="dave@example.com")
        refresh_token = create_refresh_token(str(user.id))

        response = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    async def test_refresh_with_access_token_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        user = await _create_user(db, email="eve@example.com")
        access_token = create_access_token(str(user.id))

        response = await client.post(REFRESH_URL, json={"refresh_token": access_token})

        assert response.status_code == 401

    async def test_refresh_with_invalid_token(self, client: AsyncClient) -> None:
        response = await client.post(REFRESH_URL, json={"refresh_token": "not.a.token"})

        assert response.status_code == 401


class TestLogout:
    async def test_logout_blacklists_token(self, client: AsyncClient, db: AsyncSession) -> None:
        user = await _create_user(db, email="frank@example.com")
        access_token = create_access_token(str(user.id))

        logout_response = await client.post(
            LOGOUT_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 204

        # Attempting to use the same token after logout should fail on a protected endpoint.
        # We verify blacklisting indirectly by calling logout again with the same token.
        second_response = await client.post(
            LOGOUT_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert second_response.status_code == 401

    async def test_logout_without_token(self, client: AsyncClient) -> None:
        response = await client.post(LOGOUT_URL)
        # HTTPBearer returns 401 or 403 depending on FastAPI version — either is acceptable
        assert response.status_code in (401, 403)


class TestProtectedRoute:
    async def test_health_is_public(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_protected_route_without_token(self, client: AsyncClient) -> None:
        # Logout endpoint requires auth — use it as a stand-in protected route
        response = await client.post(LOGOUT_URL)
        assert response.status_code in (401, 403)
