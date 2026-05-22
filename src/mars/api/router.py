from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from mars.api.dependencies import get_pipeline
from mars.models.s2 import Paper
from mars.schemas.event import (
    ClusterAssignment,
    ClusterGroup,
    PipelineState,
    QueryRequest,
    StageName,
)
from mars.schemas.persona import PersonaAgent
from mars.services.pipeline import NotFoundError, PipelineService, PrerequisiteError

router = APIRouter(prefix="/api/v1/queries", tags=["queries"])


@router.post("")
async def create_query(
    request: QueryRequest,
    pipeline: PipelineService = Depends(get_pipeline),
) -> PipelineState:
    """Create a query and run the extract + expand stages."""
    return await pipeline.create_query(request.query)


@router.get("/{query_id}")
async def get_query(
    query_id: str,
    pipeline: PipelineService = Depends(get_pipeline),
) -> PipelineState:
    try:
        return pipeline.get_state(query_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{query_id}/events")
async def stream_events(
    query_id: str,
    pipeline: PipelineService = Depends(get_pipeline),
) -> StreamingResponse:
    """Server-sent event stream of PipelineEvents for a query."""
    try:
        pipeline.get_state(query_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_stream() -> AsyncIterator[str]:
        async for event in pipeline.subscribe(query_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _run_stage(
    query_id: str, stage: StageName, pipeline: PipelineService
) -> PipelineState:
    try:
        return await pipeline.run_stage(query_id, stage)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{query_id}/retrieve")
async def run_retrieve(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> PipelineState:
    return await _run_stage(query_id, StageName.RETRIEVE, pipeline)


@router.post("/{query_id}/clusters")
async def run_clusters(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> PipelineState:
    return await _run_stage(query_id, StageName.CLUSTER, pipeline)


@router.post("/{query_id}/personas")
async def run_personas(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> PipelineState:
    return await _run_stage(query_id, StageName.PERSONA, pipeline)


def _artifact(query_id: str, stage: StageName, pipeline: PipelineService):
    try:
        return pipeline.get_artifact(query_id, stage)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{query_id}/papers")
async def get_papers(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> list[Paper]:
    return _artifact(query_id, StageName.RETRIEVE, pipeline)


@router.get("/{query_id}/clusters")
async def get_clusters(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> ClusterAssignment:
    clusters: dict[int, list[Paper]] = _artifact(query_id, StageName.CLUSTER, pipeline)
    groups = [
        ClusterGroup(cluster_id=cid, paper_ids=[p.id for p in papers])
        for cid, papers in sorted(clusters.items())
        if cid != -1
    ]
    noise = [p.id for p in clusters.get(-1, [])]
    return ClusterAssignment(clusters=groups, noise_paper_ids=noise)


@router.get("/{query_id}/personas")
async def get_personas(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> list[PersonaAgent]:
    return _artifact(query_id, StageName.PERSONA, pipeline)
