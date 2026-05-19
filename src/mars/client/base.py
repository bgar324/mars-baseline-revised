import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from mars.config.client import ClientConfig


class RateLimiter:
    """Enforce a minimum interval between requests."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._last_request = 0.0

    async def wait(self) -> None:
        """Sleep if needed to respect the minimum interval."""
        if self.min_interval <= 0:
            return

        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()


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
