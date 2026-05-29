from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, StringConstraints

from mars.models.persona import PersonaAgent


TurnType = Literal["propose", "respond", "refine"]
ResponseAction = Literal["challenge", "support", "concede"]
DebateAction = Literal["accept", "branch", "close"]
Outcome = Literal["question", "disagreement", "assumption"]
CycleStatus = Literal["pending", "running", "awaiting", "complete"]
SteerType = Literal["emphasize", "reframe"]

SynthesisItem = Annotated[str, StringConstraints(max_length=160)]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Citation(BaseModel):
    paper_id: str
    span: str | None = None


class Steer(BaseModel):
    type: SteerType
    text: str
    agent_id: str
    cycle_id: str


class AgentTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: uuid4().hex)
    cycle_id: str
    agent_id: str
    turn_type: TurnType
    response_action: ResponseAction | None = None
    target_turn_id: str | None = None
    claim: str
    rationale: str
    evidence: list[Citation] = Field(default_factory=list)
    message: str
    created_at: datetime = Field(default_factory=_utcnow)


class AgentTurnInput(BaseModel):
    """The parts of a turn the agent writes; the system fills in the rest."""

    turn_type: TurnType
    response_action: ResponseAction | None = None
    target_turn_id: str | None = None
    claim: str = Field(
        description="Your central position in one sentence.", max_length=400
    )
    rationale: str = Field(
        description="Why you hold it — 2-3 sentences.", max_length=800
    )
    evidence: list[Citation] = Field(default_factory=list, max_length=4)
    message: str = Field(
        description="Your spoken turn — 1-2 short sentences in plain language.",
        max_length=350,
    )


class Branch(BaseModel):
    label: str = Field(description="3-6 word scannable label.", max_length=120)
    rationale: str = Field(
        description="One sentence on what motivates this branch.", max_length=400
    )
    outcome: Outcome
    focal_claim: str = Field(
        description="The claim the next cycle would debate, one sentence.",
        max_length=400,
    )
    agents: list[str] | None = None


class DebateSynthesis(BaseModel):
    cycle_id: str
    points_of_agreement: list[SynthesisItem] = Field(default_factory=list, max_length=5)
    points_of_disagreement: list[SynthesisItem] = Field(
        default_factory=list, max_length=5
    )
    questions: list[SynthesisItem] = Field(default_factory=list, max_length=5)
    candidate_hypotheses: list[SynthesisItem] = Field(
        default_factory=list, max_length=3
    )
    branches: list[Branch] = Field(default_factory=list, max_length=3)


class Stance(BaseModel):
    summary: str = Field(
        description="Your position now, one or two short sentences.", max_length=300
    )
    claims: list[str] = Field(default_factory=list, max_length=6)
    premises: list[str] = Field(default_factory=list, max_length=6)
    conflicts: list[str] = Field(default_factory=list, max_length=6)
    cycle_id: str


class AgentState(BaseModel):
    agent_id: str
    history: list[AgentTurn] = Field(default_factory=list)
    stance: Stance | None = None
    expansions: int = 0


class Cycle(BaseModel):
    cycle_id: str = Field(default_factory=lambda: uuid4().hex)
    parent_cycle_id: str | None = None
    focal_claim: str
    agent_ids: list[str]
    turns: list[AgentTurn] = Field(default_factory=list)
    synthesis: DebateSynthesis | None = None
    status: CycleStatus = "pending"
    steers: list[Steer] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class DebateDecision(BaseModel):
    cycle_id: str
    action: DebateAction
    hypothesis: str | None = None
    branch: Branch | None = None


class Debate(BaseModel):
    debate_id: str = Field(default_factory=lambda: uuid4().hex)
    root_focal_claim: str
    agents: list[PersonaAgent]
    cycles: dict[str, Cycle] = Field(default_factory=dict)
    hypotheses: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
