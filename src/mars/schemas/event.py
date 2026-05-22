from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class StageName(str, Enum):
    EXTRACT = "extract"
    EXPAND = "expand"
    RETRIEVE = "retrieve"
    CLUSTER = "cluster"
    PERSONA = "persona"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class StageNode(BaseModel, Generic[T]):
    stage: StageName
    status: StageStatus
    result: T | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PipelineState(BaseModel):
    query_id: str
    stages: dict[StageName, StageNode]
    created_at: datetime
    updated_at: datetime


class EventType(str, Enum):
    QUERY_DECOMPOSED = "query.decomposed"
    QUERY_EXPANDED = "query.expanded"
    PAPERS_RETRIEVED = "papers.retrieved"
    CLUSTERS_GENERATED = "clusters.generated"
    PERSONAS_CREATED = "personas.created"
    STAGE_STARTED = "stage.started"
    STAGE_FAILED = "stage.failed"


class PipelineEvent(BaseModel):
    event: EventType
    query_id: str
    stage: StageName | None = None
    payload: Any = None
    timestamp: datetime


PIPELINE_GRAPH: dict[StageName, list[StageName]] = {
    StageName.EXTRACT: [],
    StageName.EXPAND: [StageName.EXTRACT],
    StageName.RETRIEVE: [StageName.EXPAND],
    StageName.CLUSTER: [StageName.RETRIEVE],
    StageName.PERSONA: [StageName.CLUSTER],
}

STAGE_EVENT: dict[StageName, EventType] = {
    StageName.EXTRACT: EventType.QUERY_DECOMPOSED,
    StageName.EXPAND: EventType.QUERY_EXPANDED,
    StageName.RETRIEVE: EventType.PAPERS_RETRIEVED,
    StageName.CLUSTER: EventType.CLUSTERS_GENERATED,
    StageName.PERSONA: EventType.PERSONAS_CREATED,
}


class QueryRequest(BaseModel):
    query: str


class ClusterGroup(BaseModel):
    cluster_id: int
    paper_ids: list[str]


class ClusterAssignment(BaseModel):
    clusters: list[ClusterGroup]
    noise_paper_ids: list[str] = Field(default_factory=list)


class DebateEventType(str, Enum):
    DEBATE_STARTED = "debate.started"
    CYCLE_STARTED = "cycle.started"
    TURN_PRODUCED = "turn.produced"
    CYCLE_SYNTHESIZED = "cycle.synthesized"
    STANCE_UPDATED = "stance.updated"
    CYCLE_AWAITING = "cycle.awaiting"
    HYPOTHESIS_ACCEPTED = "hypothesis.accepted"
    CYCLE_CLOSED = "cycle.closed"
    CYCLE_BRANCHED = "cycle.branched"
    CORPUS_EXPANDED = "corpus.expanded"


class DebateEvent(BaseModel):
    event: DebateEventType
    debate_id: str
    cycle_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
