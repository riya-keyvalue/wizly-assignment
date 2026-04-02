from __future__ import annotations

import os

# Default env for Settings() before any `app` import; does not override existing variables.
for _key, _val in {
    "SECRET_KEY": "pytest-secret-key-at-least-32-characters-long",
    "JWT_SECRET_KEY": "pytest-jwt-secret-key-32-characters-min",
    "POSTGRES_USER": "wizly",
    "POSTGRES_PASSWORD": "wizly",
    "POSTGRES_DB": "wizly",
    "DATABASE_URL": "postgresql+asyncpg://wizly:wizly@localhost:5432/wizly",
    "QDRANT_URL": "http://localhost:6333",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_ENDPOINT_URL": "http://127.0.0.1:4566",
    "S3_BUCKET_NAME": "test-bucket",
    "SKIP_CHUNKER_WARMUP": "true",
}.items():
    os.environ.setdefault(_key, _val)

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models.base import Base

# Use SQLite in-memory for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(async_engine) -> AsyncSession:  # type: ignore[no-untyped-def]
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncClient:  # type: ignore[no-untyped-def]
    async def override_get_db() -> AsyncSession:  # type: ignore[misc]
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
