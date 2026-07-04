import asyncio
from collections.abc import AsyncIterator, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger as _logger

from mars.api.dependencies import get_pipeline
from mars.models.debate import Debate, Synthesis
from mars.models.persona import Persona
from mars.models.s2 import Paper
from mars.schemas.event import (
    ClusterAssignment,
    ClusterGroup,
    DebateRunRequest,
    PipelineState,
    QueryRequest,
    SessionSnapshotRequest,
    StageName,
)
from mars.schemas.query import ExtractedQuery
from mars.workflow.base import WorkflowContext
from mars.workflow.pipeline import NotFoundError, Pipeline

query_router = APIRouter(prefix="/api/v1/queries", tags=["queries"])

_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _spawn(coro: Coroutine[Any, Any, Any]) -> None:
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_on_task_done)


def _on_task_done(task: asyncio.Task) -> None:
    _BACKGROUND_TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        _logger.opt(exception=exc).error("background pipeline task crashed")


def require_state(query_id: str, pipeline: Pipeline) -> PipelineState:
    try:
        return pipeline.get_state(query_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def require_context(query_id: str, pipeline: Pipeline) -> WorkflowContext:
    try:
        return pipeline.get_context(query_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@query_router.post("")
async def create_query(
    request: QueryRequest,
    pipeline: Pipeline = Depends(get_pipeline),
) -> PipelineState:
    state = pipeline.create_query(request.query, request.mode)
    await pipeline.persist_session(state.query_id)
    if request.mode == "manual":
        _spawn(pipeline.run_all(state.query_id, stop_before=StageName.DEBATE))
    else:
        _spawn(pipeline.run_all(state.query_id))
    return state


@query_router.post("/{query_id}/debate")
async def run_debate(
    query_id: str,
    request: DebateRunRequest,
    pipeline: Pipeline = Depends(get_pipeline),
) -> PipelineState:
    ctx = require_context(query_id, pipeline)
    if request.personas:
        ctx.personas = request.personas
    else:
        pool = ctx.persona_pool or ctx.personas
        chosen = set(request.cluster_ids)
        ctx.personas = [p for p in pool if p.cluster_id in chosen]
    if len(ctx.personas) < 2:
        raise HTTPException(
            status_code=400,
            detail="Select at least 2 researchers to debate.",
        )
    if len(ctx.personas) > 4:
        raise HTTPException(
            status_code=400,
            detail="Select no more than 4 researchers to debate.",
        )
    await pipeline.persist_session(query_id)
    _spawn(pipeline.run_stage(query_id, StageName.DEBATE))
    return require_state(query_id, pipeline)


@query_router.get("/{query_id}/export")
async def export_query(
    query_id: str,
    pipeline: Pipeline = Depends(get_pipeline),
) -> dict[str, Any]:
    try:
        payload = pipeline.export_session(query_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pipeline.persist_session(query_id, export_payload=payload)
    return payload


@query_router.post("/{query_id}/export")
async def save_and_export_query(
    query_id: str,
    request: SessionSnapshotRequest,
    pipeline: Pipeline = Depends(get_pipeline),
) -> dict[str, Any]:
    try:
        payload = pipeline.export_session(
            query_id, frontend_snapshot=request.frontend_snapshot
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pipeline.persist_session(
        query_id,
        frontend_snapshot=request.frontend_snapshot,
        export_payload=payload,
    )
    return payload


@query_router.get("/{query_id}")
async def get_query(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> PipelineState:
    return require_state(query_id, pipeline)


@query_router.get("/{query_id}/events")
async def stream_events(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> StreamingResponse:
    require_state(query_id, pipeline)

    async def event_stream() -> AsyncIterator[str]:
        async for event in pipeline.subscribe(query_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@query_router.get("/{query_id}/extraction")
async def get_extraction(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> ExtractedQuery:
    extracted = require_context(query_id, pipeline).extracted
    if extracted is None:
        raise HTTPException(status_code=404, detail="extraction not available yet")
    return extracted


@query_router.get("/{query_id}/papers")
async def get_papers(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> list[Paper]:
    return require_context(query_id, pipeline).papers


@query_router.get("/{query_id}/clusters")
async def get_clusters(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> ClusterAssignment:
    clusters = require_context(query_id, pipeline).clusters or {}
    groups = [
        ClusterGroup(cluster_id=cid, paper_ids=[p.id for p in papers])
        for cid, papers in sorted(clusters.items())
        if cid != -1
    ]
    noise = [p.id for p in clusters.get(-1, [])]
    return ClusterAssignment(clusters=groups, noise_paper_ids=noise)


@query_router.get("/{query_id}/personas")
async def get_personas(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> list[Persona]:
    return require_context(query_id, pipeline).personas


@query_router.get("/{query_id}/persona-pool")
async def get_persona_pool(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> list[Persona]:
    ctx = require_context(query_id, pipeline)
    return ctx.persona_pool or ctx.personas


@query_router.get("/{query_id}/perspectives")
async def get_perspectives(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> list[int]:
    return require_context(query_id, pipeline).perspectives or []


@query_router.get("/{query_id}/debate")
async def get_debate(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> Debate:
    debate = require_context(query_id, pipeline).debate
    if debate is None:
        raise HTTPException(status_code=404, detail="debate not available yet")
    return debate


@query_router.get("/{query_id}/hypotheses")
async def get_hypotheses(
    query_id: str, pipeline: Pipeline = Depends(get_pipeline)
) -> Synthesis:
    cycle = require_context(query_id, pipeline).cycle
    synthesis = cycle.synthesis if cycle else None
    if synthesis is None:
        raise HTTPException(status_code=404, detail="hypotheses not available yet")
    return synthesis
