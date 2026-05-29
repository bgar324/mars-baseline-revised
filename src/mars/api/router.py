from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from mars.api.dependencies import get_debate_service, get_pipeline
from mars.models.debate import AgentTurn, Cycle, Debate, DebateDecision, Steer
from mars.models.persona import PersonaAgent
from mars.models.s2 import Paper
from mars.schemas.debate import DebateRequest, ProposeRequest
from mars.schemas.event import (
    ClusterAssignment,
    ClusterGroup,
    PipelineState,
    QueryRequest,
    StageName,
)
from mars.schemas.query import ClaimUpdate
from mars.services.debate import (
    DebateError,
    DebateService,
)
from mars.services.debate import (
    NotFoundError as DebateNotFoundError,
)
from mars.services.pipeline import NotFoundError, PipelineService, PrerequisiteError

query_router = APIRouter(prefix="/api/v1/queries", tags=["queries"])


@query_router.post("")
async def create_query(
    request: QueryRequest,
    pipeline: PipelineService = Depends(get_pipeline),
) -> PipelineState:
    """Create a query and run the extract + expand stages."""
    return await pipeline.create_query(request.query)


@query_router.get("/{query_id}")
async def get_query(
    query_id: str,
    pipeline: PipelineService = Depends(get_pipeline),
) -> PipelineState:
    try:
        return pipeline.get_state(query_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@query_router.get("/{query_id}/events")
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


@query_router.post("/{query_id}/retrieve")
async def run_retrieve(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> PipelineState:
    return await _run_stage(query_id, StageName.RETRIEVE, pipeline)


@query_router.post("/{query_id}/clusters")
async def run_clusters(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> PipelineState:
    return await _run_stage(query_id, StageName.CLUSTER, pipeline)


@query_router.post("/{query_id}/personas")
async def run_personas(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> PipelineState:
    return await _run_stage(query_id, StageName.PERSONA, pipeline)


def _artifact(query_id: str, stage: StageName, pipeline: PipelineService):
    try:
        return pipeline.get_artifact(query_id, stage)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@query_router.get("/{query_id}/papers")
async def get_papers(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> list[Paper]:
    return _artifact(query_id, StageName.RETRIEVE, pipeline)


@query_router.get("/{query_id}/clusters")
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


@query_router.get("/{query_id}/personas")
async def get_personas(
    query_id: str, pipeline: PipelineService = Depends(get_pipeline)
) -> list[PersonaAgent]:
    return _artifact(query_id, StageName.PERSONA, pipeline)


@query_router.put("/{query_id}/claim")
async def update_claim(
    query_id: str,
    update: ClaimUpdate,
    pipeline: PipelineService = Depends(get_pipeline),
) -> PipelineState:
    try:
        return pipeline.update_claim(query_id, update.claim)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


debate_router = APIRouter(prefix="/api/v1/debates", tags=["debates"])


def _http_error(exc: DebateError) -> HTTPException:
    status = 404 if isinstance(exc, DebateNotFoundError) else 409
    return HTTPException(status_code=status, detail=str(exc))


@debate_router.post("")
async def create_debate(
    request: DebateRequest,
    service: DebateService = Depends(get_debate_service),
    pipeline: PipelineService = Depends(get_pipeline),
) -> Debate:
    """Create a debate with its root cycle and start the event stream."""
    cluster_papers = request.cluster_papers
    if not cluster_papers and request.query_id is not None:
        clusters: dict[int, list[Paper]] = _artifact(
            request.query_id, StageName.CLUSTER, pipeline
        )
        cluster_papers = {
            str(cid): papers for cid, papers in clusters.items() if cid != -1
        }
    return await service.start(
        focal_claim=request.focal_claim,
        agents=request.agents,
        cluster_papers=cluster_papers,
    )


@debate_router.get("/{debate_id}")
async def get_debate(
    debate_id: str,
    service: DebateService = Depends(get_debate_service),
) -> Debate:
    try:
        return service.get_debate(debate_id)
    except DebateError as exc:
        raise _http_error(exc) from exc


@debate_router.get("/{debate_id}/cycles/{cycle_id}")
async def get_cycle(
    debate_id: str,
    cycle_id: str,
    service: DebateService = Depends(get_debate_service),
) -> Cycle:
    try:
        return service.get_cycle(debate_id, cycle_id)
    except DebateError as exc:
        raise _http_error(exc) from exc


@debate_router.post("/{debate_id}/cycles/{cycle_id}/run")
async def run_cycle(
    debate_id: str,
    cycle_id: str,
    service: DebateService = Depends(get_debate_service),
) -> Cycle:
    try:
        return await service.run_cycle(debate_id=debate_id, cycle_id=cycle_id)
    except DebateError as exc:
        raise _http_error(exc) from exc


@debate_router.post("/{debate_id}/cycles/{cycle_id}/propose")
async def propose_turn(
    debate_id: str,
    cycle_id: str,
    request: ProposeRequest,
    service: DebateService = Depends(get_debate_service),
) -> AgentTurn:
    try:
        return await service.propose(
            debate_id=debate_id,
            cycle_id=cycle_id,
            agent_id=request.agent_id,
            steers=request.steers,
        )
    except DebateError as exc:
        raise _http_error(exc) from exc


@debate_router.post("/{debate_id}/steer")
async def steer_debate(
    debate_id: str,
    decision: DebateDecision,
    service: DebateService = Depends(get_debate_service),
) -> Cycle | None:
    try:
        return await service.steer(debate_id=debate_id, decision=decision)
    except DebateError as exc:
        raise _http_error(exc) from exc


@debate_router.put("/{debate_id}/cycles/{cycle_id}/steers")
async def set_cycle_steers(
    debate_id: str,
    cycle_id: str,
    steers: list[Steer],
    service: DebateService = Depends(get_debate_service),
) -> Cycle:
    try:
        return await service.set_steers(
            debate_id=debate_id, cycle_id=cycle_id, steers=steers
        )
    except DebateError as exc:
        raise _http_error(exc) from exc


@debate_router.get("/{debate_id}/events")
async def stream_debate_events(
    debate_id: str,
    service: DebateService = Depends(get_debate_service),
) -> StreamingResponse:
    """Server-sent event stream of DebateEvents for a debate."""
    try:
        service.get_debate(debate_id)
    except DebateError as exc:
        raise _http_error(exc) from exc

    async def event_stream() -> AsyncIterator[str]:
        async for event in service.subscribe(debate_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
