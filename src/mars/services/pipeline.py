import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from mars.schemas.event import (
    PIPELINE_GRAPH,
    STAGE_EVENT,
    EventType,
    PipelineEvent,
    PipelineState,
    StageName,
    StageNode,
    StageStatus,
)
from mars.schemas.query import ExtractedQuery
from mars.services.cluster import ClusterService
from mars.services.persona import PersonaService
from mars.services.query import QueryService
from mars.services.retrieval import RetrievalService


class PipelineError(Exception):
    ...


class NotFoundError(PipelineError):
    ...


class PrerequisiteError(PipelineError):
    ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _summary(stage: StageName, result: Any) -> dict[str, Any]:
    if stage is StageName.EXTRACT:
        return {"spans": len(result.spans), "claim": result.claim}
    if stage is StageName.EXPAND:
        expansion, questions = result
        return {"domain": expansion.domain, "questions": len(questions.questions)}
    if stage is StageName.RETRIEVE:
        return {"papers": len(result)}
    if stage is StageName.CLUSTER:
        return {"clusters": sum(1 for cid in result if cid != -1)}
    if stage is StageName.PERSONA:
        return {"personas": len(result)}
    return {}


class PipelineService:
    def __init__(
        self,
        *,
        query: QueryService,
        retrieval: RetrievalService,
        cluster: ClusterService,
        persona: PersonaService,
    ) -> None:
        self._query = query
        self._retrieval = retrieval
        self._cluster = cluster
        self._persona = persona
        self._states: dict[str, PipelineState] = {}
        self._text: dict[str, str] = {}
        self._artifacts: dict[str, dict[StageName, Any]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[PipelineEvent]]] = {}

    async def create_query(self, text: str) -> PipelineState:
        query_id = uuid4().hex
        now = _now()
        self._states[query_id] = PipelineState(
            query_id=query_id,
            stages={
                s: StageNode(stage=s, status=StageStatus.PENDING) for s in StageName
            },
            created_at=now,
            updated_at=now,
        )
        self._text[query_id] = text
        self._artifacts[query_id] = {}
        self._subscribers.setdefault(query_id, set())

        await self._run(query_id, StageName.EXTRACT)
        if self._stage_done(query_id, StageName.EXTRACT):
            await self._run(query_id, StageName.EXPAND)
        return self._states[query_id]

    async def run_stage(self, query_id: str, stage: StageName) -> PipelineState:
        state = self._require(query_id)
        for dep in PIPELINE_GRAPH[stage]:
            if state.stages[dep].status is not StageStatus.COMPLETE:
                raise PrerequisiteError(
                    f"stage '{stage.value}' requires '{dep.value}' to complete first"
                )
        if state.stages[stage].status is StageStatus.COMPLETE:
            return state
        await self._run(query_id, stage)
        return self._states[query_id]

    def get_state(self, query_id: str) -> PipelineState:
        return self._require(query_id)

    def get_artifact(self, query_id: str, stage: StageName) -> Any:
        state = self._require(query_id)
        if state.stages[stage].status is not StageStatus.COMPLETE:
            raise NotFoundError(f"stage '{stage.value}' has not completed")
        return self._artifacts[query_id][stage]

    def update_claim(self, query_id: str, claim: str) -> PipelineState:
        state = self._require(query_id)
        node = state.stages[StageName.EXTRACT]
        if node.status is not StageStatus.COMPLETE:
            raise PrerequisiteError("stage 'extract' has not completed")
        extracted: ExtractedQuery = self._artifacts[query_id][StageName.EXTRACT]
        updated = extracted.model_copy(update={"claim": claim})
        self._artifacts[query_id][StageName.EXTRACT] = updated
        node.result = _summary(StageName.EXTRACT, updated)
        self._touch(query_id)
        return state

    async def subscribe(self, query_id: str) -> AsyncIterator[PipelineEvent]:
        self._require(query_id)
        queue: asyncio.Queue[PipelineEvent] = asyncio.Queue()
        self._subscribers.setdefault(query_id, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.get(query_id, set()).discard(queue)

    def _require(self, query_id: str) -> PipelineState:
        state = self._states.get(query_id)
        if state is None:
            raise NotFoundError(f"query '{query_id}' not found")
        return state

    def _stage_done(self, query_id: str, stage: StageName) -> bool:
        return self._states[query_id].stages[stage].status is StageStatus.COMPLETE

    def _touch(self, query_id: str) -> None:
        self._states[query_id].updated_at = _now()

    async def _emit(self, query_id: str, event: PipelineEvent) -> None:
        for queue in list(self._subscribers.get(query_id, ())):
            await queue.put(event)

    async def _run(self, query_id: str, stage: StageName) -> None:
        node = self._states[query_id].stages[stage]
        node.status = StageStatus.RUNNING
        node.started_at = _now()
        node.error = None
        self._touch(query_id)
        await self._emit(
            query_id,
            PipelineEvent(
                event=EventType.STAGE_STARTED,
                query_id=query_id,
                stage=stage,
                timestamp=_now(),
            ),
        )
        try:
            result = await self._execute(query_id, stage)
        except Exception as exc:
            node.status = StageStatus.FAILED
            node.error = str(exc)
            node.completed_at = _now()
            self._touch(query_id)
            await self._emit(
                query_id,
                PipelineEvent(
                    event=EventType.STAGE_FAILED,
                    query_id=query_id,
                    stage=stage,
                    payload={"error": str(exc)},
                    timestamp=_now(),
                ),
            )
            return

        self._artifacts[query_id][stage] = result
        node.result = _summary(stage, result)
        node.status = StageStatus.COMPLETE
        node.completed_at = _now()
        self._touch(query_id)
        await self._emit(
            query_id,
            PipelineEvent(
                event=STAGE_EVENT[stage],
                query_id=query_id,
                stage=stage,
                payload=_summary(stage, result),
                timestamp=_now(),
            ),
        )

    async def _execute(self, query_id: str, stage: StageName) -> Any:
        arts = self._artifacts[query_id]
        if stage is StageName.EXTRACT:
            return await self._query.extract(self._text[query_id])
        if stage is StageName.EXPAND:
            return await self._query.expand(arts[StageName.EXTRACT])
        if stage is StageName.RETRIEVE:
            expansion, questions = arts[StageName.EXPAND]
            return await self._retrieval.retrieve(
                arts[StageName.EXTRACT], expansion, questions
            )
        if stage is StageName.CLUSTER:
            return await asyncio.to_thread(
                self._cluster.cluster, arts[StageName.RETRIEVE]
            )
        if stage is StageName.PERSONA:
            extracted: ExtractedQuery = arts[StageName.EXTRACT]
            return await self._persona.synthesize(
                arts[StageName.CLUSTER], extracted.claim
            )
        raise PipelineError(f"unknown stage: {stage}")
