from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from mars.llm.providers.base import TokenUsage
from mars.models.persona import Persona


class StageName(str, Enum):
    EXTRACT = "extract"
    RETRIEVE = "retrieve"
    CLUSTER = "cluster"
    PERSONA = "persona"
    DEBATE = "debate"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    FAILED = "failed"


class StepNode(BaseModel):
    name: str
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    usage: TokenUsage | None = None


class StageNode(BaseModel):
    stage: StageName
    status: StageStatus = StageStatus.PENDING
    steps: dict[str, StepNode] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    usage: TokenUsage | None = None


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
    STAGE_SKIPPED = "stage.skipped"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    STEP_STARTED = "step.started"
    STEP_SKIPPED = "step.skipped"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    STEP_PROGRESS = "step.progress"
    AGENT_THINKING = "agent.thinking"
    AGENT_TURN = "agent.turn"


class PipelineEvent(BaseModel):
    event: EventType
    query_id: str
    stage: StageName | None = None
    step: str | None = None
    payload: Any = None
    timestamp: datetime


STAGE_EVENT: dict[StageName, EventType] = {
    StageName.EXTRACT: EventType.QUERY_DECOMPOSED,
    StageName.RETRIEVE: EventType.PAPERS_RETRIEVED,
    StageName.CLUSTER: EventType.CLUSTERS_GENERATED,
    StageName.PERSONA: EventType.PERSONAS_CREATED,
}


class QueryRequest(BaseModel):
    query: str
    mode: Literal["auto", "manual"] = "auto"
    condition: Literal["mars", "baseline"] = "mars"
    test_mode: bool = False


class DebateRunRequest(BaseModel):
    cluster_ids: list[int] = Field(default_factory=list)
    personas: list[Persona] = Field(default_factory=list)


class SessionSnapshotRequest(BaseModel):
    frontend_snapshot: dict[str, Any] | None = None


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
    CYCLE_ASSESSED = "cycle.assessed"
    CYCLE_ADJUDICATED = "cycle.adjudicated"
    CYCLE_SYNTHESIZED = "cycle.synthesized"


class DebateEvent(BaseModel):
    event: DebateEventType
    debate_id: str
    cycle_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
