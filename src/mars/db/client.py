from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import AsyncClient

from mars.config.settings import SupabaseSettings


class SupabaseClient:
    def __init__(
        self,
        settings: SupabaseSettings,
        *,
        use_secret_key: bool = False,
    ) -> None:
        if use_secret_key and settings.secret_key is None:
            raise ValueError(
                "Supabase secret key requested but SUPABASE_SECRET_KEY is not set."
            )

        key_secret = settings.secret_key if use_secret_key else settings.publishable_key
        assert key_secret is not None

        self._url = settings.url
        self._key = key_secret.get_secret_value()
        self._client: "AsyncClient | None" = None

    async def __aenter__(self) -> "SupabaseClient":
        from supabase import acreate_client

        self._client = await acreate_client(self._url, self._key)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            close = getattr(self._client, "aclose", None) or getattr(
                self._client, "close", None
            )
            if close is not None:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            self._client = None

    @property
    def _c(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "SupabaseClient must be used as an async context manager."
            )
        return self._client

    @property
    def client(self) -> AsyncClient:
        return self._c

    @property
    def auth(self) -> Any:
        return self._c.auth

    @property
    def storage(self) -> Any:
        return self._c.storage

    def table(self, name: str) -> Any:
        return self._c.table(name)

    def rpc(self, fn: str, params: dict[str, Any] | None = None) -> Any:
        return self._c.rpc(fn, params or {})

    def __repr__(self) -> str:
        status = "connected" if self._client is not None else "uninitialised"
        return f"SupabaseClient(url={self._url!r}, status={status!r})"
