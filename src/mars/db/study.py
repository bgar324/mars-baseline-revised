from __future__ import annotations

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
    def __init__(self, settings: SupabaseSettings) -> None:
        self._settings = settings
        self.enabled = _configured(settings)
        if not self.enabled:
            logger.warning(
                "study persistence disabled; set SUPABASE_URL and "
                "SUPABASE_SECRET_KEY or SUPABASE_PUBLISHABLE_KEY"
            )

    async def _execute(self, table: str, op: str, payload: Any) -> None:
        if not self.enabled:
            return
        try:
            async with SupabaseClient(
                self._settings, use_secret_key=self._settings.secret_key is not None
            ) as db:
                if table == "study_sessions" and op == "upsert":
                    query = db.table(table).upsert(payload, on_conflict="query_id")
                else:
                    query = getattr(db.table(table), op)(payload)
                await query.execute()
        except Exception as exc:
            logger.warning("study persistence failed on {}.{}: {}", table, op, exc)

    async def upsert_session(
        self,
        *,
        state: PipelineState,
        ctx: WorkflowContext,
        backend_snapshot: dict[str, Any],
        frontend_snapshot: dict[str, Any] | None = None,
        export_payload: dict[str, Any] | None = None,
    ) -> None:
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
        await self._execute("study_sessions", "upsert", payload)

    async def record_event(self, event: PipelineEvent) -> None:
        payload = {
            "query_id": event.query_id,
            "event_type": event.event.value,
            "stage": event.stage.value if event.stage else None,
            "step": event.step,
            "payload": event.payload if event.payload is not None else {},
            "occurred_at": event.timestamp.isoformat(),
        }
        await self._execute("study_session_events", "insert", payload)
