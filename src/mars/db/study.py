from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from mars.config.settings import SupabaseSettings
from mars.db.client import SupabaseClient
from mars.schemas.event import PipelineEvent, PipelineState, StageName
from mars.workflow.base import WorkflowContext


def _configured(settings: SupabaseSettings) -> bool:
    return bool(settings.url and (settings.secret_key or settings.publishable_key))


def _status(state: PipelineState) -> tuple[str, str | None]:
    last_error: str | None = None
    statuses = [stage.status.value for stage in state.stages.values()]
    for stage in state.stages.values():
        if stage.error:
            last_error = stage.error
    if "failed" in statuses:
        return "failed", last_error
    if "running" in statuses:
        return "running", None
    persona = state.stages.get(StageName.PERSONA)
    if persona is not None and persona.status.value == "complete":
        debate = state.stages.get(StageName.DEBATE)
        if debate is not None and debate.status.value == "pending":
            return "ready_for_debate", None
    if statuses and all(s in {"complete", "skipped"} for s in statuses):
        return "complete", None
    if any(s == "complete" for s in statuses):
        return "active", None
    return "created", None


class StudySessionRecorder:
    """Persists study sessions and pipeline events to Supabase.

    Writes are drained by a single background worker over one long-lived
    Supabase client, so the hot pipeline path never blocks on a network
    round-trip (or on spinning up a fresh client per call). Session upserts
    are coalesced per ``query_id`` — only the freshest snapshot is written,
    which drops the redundant full-corpus uploads the pipeline emits at every
    stage boundary. Callers that need durability before returning (the export
    and chat endpoints) pass ``wait=True`` and await the enqueued write.
    """

    def __init__(self, settings: SupabaseSettings) -> None:
        self._settings = settings
        self.enabled = _configured(settings)
        self._use_secret = settings.secret_key is not None
        self._db: SupabaseClient | None = None
        self._queue: asyncio.Queue[tuple[str, Any, asyncio.Future | None]] | None = None
        self._worker: asyncio.Task | None = None
        self._pending: dict[str, dict[str, Any]] = {}
        if not self.enabled:
            logger.warning(
                "study persistence disabled; set SUPABASE_URL and "
                "SUPABASE_SECRET_KEY or SUPABASE_PUBLISHABLE_KEY"
            )

    async def _client(self) -> SupabaseClient:
        if self._db is None:
            db = SupabaseClient(self._settings, use_secret_key=self._use_secret)
            await db.__aenter__()
            self._db = db
        return self._db

    async def _write(self, table: str, op: str, payload: Any) -> None:
        try:
            db = await self._client()
            if table == "study_sessions" and op == "upsert":
                query = db.table(table).upsert(payload, on_conflict="query_id")
            else:
                query = getattr(db.table(table), op)(payload)
            await query.execute()
        except Exception as exc:
            logger.warning("study persistence failed on {}.{}: {}", table, op, exc)
            # Drop the client so the next write reconnects rather than reusing
            # a socket the server may already have closed.
            db, self._db = self._db, None
            if db is not None:
                try:
                    await db.__aexit__(None, None, None)
                except Exception:
                    pass

    def _ensure_worker(self) -> asyncio.Queue:
        if self._queue is None:
            self._queue = asyncio.Queue()
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._worker_loop())
        return self._queue

    async def _worker_loop(self) -> None:
        assert self._queue is not None
        while True:
            kind, arg, done = await self._queue.get()
            try:
                if kind == "event":
                    await self._write("study_session_events", "insert", arg)
                elif kind == "session":
                    payload = self._pending.pop(arg, None)
                    if payload is not None:
                        await self._write("study_sessions", "upsert", payload)
            finally:
                if done is not None and not done.done():
                    done.set_result(None)
                self._queue.task_done()

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
        if not self.enabled:
            return
        status, last_error = _status(state)
        payload: dict[str, Any] = {
            "query_id": state.query_id,
            "condition": ctx.condition,
            "mode": ctx.mode,
            "research_problem": ctx.raw_text,
            "status": status,
            "last_error": last_error,
            "backend_snapshot": backend_snapshot,
        }
        if frontend_snapshot is not None:
            payload["frontend_snapshot"] = frontend_snapshot
        if export_payload is not None:
            payload["export_payload"] = export_payload

        # Coalesce by query_id: later fields win, sticky fields (frontend /
        # export payloads) survive plainer upserts that omit them.
        self._pending.setdefault(state.query_id, {}).update(payload)
        queue = self._ensure_worker()
        done = asyncio.get_running_loop().create_future() if wait else None
        queue.put_nowait(("session", state.query_id, done))
        if done is not None:
            await done

    async def record_event(self, event: PipelineEvent) -> None:
        if not self.enabled:
            return
        payload = {
            "query_id": event.query_id,
            "event_type": event.event.value,
            "stage": event.stage.value if event.stage else None,
            "step": event.step,
            "payload": event.payload if event.payload is not None else {},
            "occurred_at": event.timestamp.isoformat(),
        }
        queue = self._ensure_worker()
        queue.put_nowait(("event", payload, None))

    async def aclose(self) -> None:
        if self._queue is not None:
            await self._queue.join()
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except (asyncio.CancelledError, Exception):
                pass
            self._worker = None
        if self._db is not None:
            try:
                await self._db.__aexit__(None, None, None)
            except Exception:
                pass
            self._db = None
