import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from mars.config.client import ClientConfig


class RateLimiter:
    """Enforce a minimum interval between requests, safe under concurrency."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._next_allowed = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """Sleep until this caller's reserved slot, spaced by min_interval."""
        if self.min_interval <= 0:
            return

        async with self._lock:
            now = time.monotonic()
            scheduled = max(now, self._next_allowed)
            self._next_allowed = scheduled + self.min_interval

        delay = scheduled - now
        if delay > 0:
            await asyncio.sleep(delay)


class BaseClient(ABC):
    """Async HTTP client with lazy session and rate limiting."""

    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self._rate_limiter = RateLimiter(config.min_request_interval)
        self._session: httpx.AsyncClient | None = None

    def auth_headers(self) -> dict[str, str]:
        """Return provider-specific auth headers. Override as needed."""
        return {}

    @property
    def session(self) -> httpx.AsyncClient:
        """Return the async session, creating it on first use."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={"User-Agent": self.config.user_agent, **self.auth_headers()},
                timeout=self.config.request_timeout,
                follow_redirects=True,
            )
        return self._session

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> Any:
        """Fetch and return provider-specific data."""

    async def aclose(self) -> None:
        """Close the async session if it was opened."""
        if self._session is not None:
            await self._session.aclose()
            self._session = None

    async def __aenter__(self) -> "BaseClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
