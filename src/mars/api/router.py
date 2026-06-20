import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from mars.api.dependencies import get_pipeline
from mars.models.debate import Debate, Synthesis
from mars.models.persona import Persona
from mars.models.s2 import Paper
from mars.schemas.event import (
    ClusterAssignment,
    ClusterGroup,
    PipelineState,
    QueryRequest,
)
from mars.schemas.query import ExtractedQuery
from mars.workflow.base import WorkflowContext
from mars.workflow.pipeline import NotFoundError, Pipeline

query_router = APIRouter(prefix="/api/v1/queries", tags=["queries"])


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
    state = pipeline.create_query(request.query)
    asyncio.create_task(pipeline.run_all(state.query_id))
    return state


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
