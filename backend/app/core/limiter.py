from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class _InMemoryRateLimiter:
    """Simple sliding-window rate limiter backed by an in-memory dict.

    Suitable for single-process deployments (prototype / dev).
    For multi-instance production, replace the store with Redis.
    """

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds
        hits = self._hits[key]
        # Evict expired timestamps
        self._hits[key] = [t for t in hits if t > window_start]
        if len(self._hits[key]) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded — max {max_requests} requests per {window_seconds}s.",
            )
        self._hits[key].append(now)


_limiter = _InMemoryRateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60):
    """Return a FastAPI dependency that enforces a per-IP rate limit.

    Usage::

        @router.post("/login")
        async def login(
            data: LoginRequest,
            db: AsyncSession = Depends(get_db),
            _rl: None = Depends(rate_limit(20, 60)),
        ):
    """

    def _dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{request.url.path}"
        _limiter.check(key, max_requests, window_seconds)

    return _dependency
