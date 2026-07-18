from __future__ import annotations

from typing import Any, Protocol

from loguru import logger

from mars.schemas.event import PipelineEvent, PipelineState
from mars.workflow.base import WorkflowContext


class AsyncCache(Protocol):
    async def get(self, key: str) -> object: ...

    async def set(
        self,
        key: str,
        value: object,
        options: dict[str, Any] | None = None,
    ) -> object: ...


class SessionCache:
    """Keep resumable pipeline snapshots without a database.

    Vercel Runtime Cache shares short-lived values across function instances.
    Outside Vercel, its SDK automatically falls back to process-local memory.
    Pipeline events are already delivered over SSE, so only the latest complete
    snapshot needs to be cached.
    """

    def __init__(
        self,
        cache: AsyncCache | None = None,
        *,
        ttl_seconds: int = 6 * 60 * 60,
    ) -> None:
        if cache is None:
            from vercel.functions import AsyncRuntimeCache

            cache = AsyncRuntimeCache(namespace="mars-session")
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def load_session(self, query_id: str) -> dict[str, Any] | None:
        try:
            snapshot = await self._cache.get(query_id)
        except Exception as exc:
            logger.warning("session cache read failed for {}: {}", query_id, exc)
            return None
        return snapshot if isinstance(snapshot, dict) else None

    async def upsert_session(
        self,
        *,
        state: PipelineState,
        ctx: WorkflowContext,
        backend_snapshot: dict[str, Any],
        frontend_snapshot: dict[str, Any] | None = None,
        export_payload: dict[str, Any] | None = None,
        wait: bool = False,
    ) -> None:
        del ctx, frontend_snapshot, export_payload, wait
        try:
            await self._cache.set(
                state.query_id,
                backend_snapshot,
                {"ttl": self._ttl_seconds},
            )
        except Exception as exc:
            logger.warning("session cache write failed for {}: {}", state.query_id, exc)

    async def record_event(self, event: PipelineEvent) -> None:
        del event

    async def aclose(self) -> None:
        return None
