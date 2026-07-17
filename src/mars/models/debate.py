from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from mars.models.persona import Persona


AgentId = str

AgentPhase = Literal["proposal", "rebuttal", "refinement"]
JudgePhase = Literal["adjudication", "synthesis"]
DebateEvent = AgentPhase | JudgePhase

SteerType = Literal["emphasize", "reframe"]
CycleStatus = Literal["pending", "running", "complete"]


class EvidenceWeight(str, Enum):
    STRENGTHENS = "strengthens"
    WEAKENS = "weakens"
    REFINES = "refines"
    DISPUTED = "disputed"
    UNRELATED = "unrelated"


class TurnAction(str, Enum):
    CHALLENGE = "challenge"
    SUPPORT = "support"
    CONCEDE = "concede"


ACTION_BY_WEIGHT: dict[EvidenceWeight, TurnAction] = {
    EvidenceWeight.STRENGTHENS: TurnAction.SUPPORT,
    EvidenceWeight.REFINES: TurnAction.SUPPORT,
    EvidenceWeight.WEAKENS: TurnAction.CONCEDE,
    EvidenceWeight.DISPUTED: TurnAction.CHALLENGE,
    EvidenceWeight.UNRELATED: TurnAction.CHALLENGE,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Steer(BaseModel):
    type: SteerType
    text: str
    agent_id: AgentId


class EvidenceSnippet(BaseModel):
    corpus_id: str = Field(
        description="S2 corpusId of the source paper. Copy verbatim into grounding."
    )
    title: str = Field(default="", description="Source paper title.")
    section: str | None = Field(
        default=None,
        description="Section name the passage came from, e.g. 'Conclusion'.",
    )
    text: str = Field(description="The passage text, about 500 words.")
    score: float | None = Field(
        default=None,
        description="Passage relevance score returned by the retrieval endpoint.",
    )
    tier: Literal[
        "primary",
        "secondary",
        "judge",
        "relation",
        "counter_internal",
        "counter_external",
    ] = Field(description="Retrieval stage that produced this passage.")


class EvidenceSet(BaseModel):
    snippets: list[EvidenceSnippet] = Field(default_factory=list)


class ScoutQueries(BaseModel):
    primary: list[str] = Field(
        min_length=2,
        max_length=2,
        description="Exactly 2 queries that find evidence to shape this agent's argument from its "
        "own cluster. Each is one short descriptive sentence.",
    )
    secondary: str = Field(
        description="One query that finds evidence to augment the argument from beyond the cluster. "
        "One short descriptive sentence.",
    )


class SearchQuery(BaseModel):
    query: str = Field(
        description="One short descriptive sentence used for semantic snippet search."
    )


class AgentResponse(BaseModel):
    evidence_weight: EvidenceWeight | None = Field(
        default=None,
        description="How the opponent's cited evidence bears on your position; null on a proposal turn.",
    )
    claim: str = Field(
        description="Your position, as one contestable sentence, calibrated to the evidence."
    )
    rationale: str = Field(
        description="One to three sentences justifying the claim from your evidence."
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="corpus_ids supporting this turn, copied verbatim.",
    )
    conceded_point: str | None = Field(
        default=None,
        description="The part of your position the evidence undermines; only when evidence_weight is weakens.",
    )
    preserved_point: str | None = Field(
        default=None,
        description="The part of your position that still holds; only when evidence_weight is weakens.",
    )
    revised_position: str | None = Field(
        default=None,
        description="Your position restated after the concession; only when evidence_weight is weakens.",
    )
    target_id: AgentId | None = Field(
        default=None,
        description="agent_id of the agent you address; null on a proposal turn.",
    )
    message: str = Field(description="Your spoken turn in plain language.")
    action: TurnAction | None = Field(
        default=None,
        description="Leave null; derived in code from evidence_weight.",
    )


class AgentTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: uuid4().hex)
    agent_id: AgentId
    phase: AgentPhase
    cycle: int = 1
    response: AgentResponse
    created_at: datetime = Field(default_factory=_utcnow)


class Stance(BaseModel):
    agent_id: str = Field(description="agent_id of the agent whose position this is.")
    position: str = Field(
        description="The agent's core position on the focal claim: the side and its central reason.",
    )


class Disagreement(BaseModel):
    agents: list[str] = Field(
        description="agent_ids on opposing sides of this disagreement. At least 2.",
    )
    point: str = Field(
        description="The precise proposition they disagree on.",
    )


class Critique(BaseModel):
    target: str = Field(
        description="agent_id of the agent whose position carries this weakness."
    )
    challenger: str = Field(
        default="",
        description="agent_id best placed to press this weakness, or '' if any opponent could.",
    )
    on_point: str = Field(
        description="The specific weakness to challenge: an unsupported step, overstated link, or "
        "unaddressed alternative.",
    )


class DebateAssessment(BaseModel):
    phase: str = Field(
        default="assessment", description="Phase that produced this assessment."
    )
    cycle: int = Field(default=1, description="Round number this assessment covers.")

    overview: str = Field(
        description="Short neutral overview of where the debate stands after the proposals."
    )
    stances: list[Stance] = Field(
        default_factory=list,
        description="One staked position per participating agent.",
    )
    points_of_agreement: list[str] = Field(
        default_factory=list,
        description="Shared propositions stated by two or more agents.",
    )
    points_of_disagreement: list[Disagreement] = Field(
        default_factory=list,
        description="Disagreements after the proposals, naming the agents and the point.",
    )
    central_conflict: str = Field(
        description="The unresolved disagreement most central to the focal claim, stated as two conflicting positions.",
    )
    critiques: list[Critique] = Field(
        default_factory=list,
        description="Who challenges whom, on what.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Open questions raised in the proposals.",
    )
    disagreement_present: bool = Field(
        default=True,
        description="Whether the proposals contest a genuine axis.",
    )


class Adjudication(BaseModel):
    phase: str = Field(
        default="adjudication", description="Phase that produced this output."
    )
    cycle: int = Field(default=1, description="Round number this covers.")

    reasoning: str = Field(
        description="A 4 to 6 sentence summary of how the debate changed the central conflict, in "
        "subject-matter terms.",
    )
    resolved: list[str] = Field(
        default_factory=list,
        description="Propositions the debate resolved, each with the condition or scope where it holds.",
    )
    unresolved: list[str] = Field(
        default_factory=list,
        description="Open questions, each naming the disputed mechanism and what would decide it.",
    )


class ClaimDecomposition(BaseModel):
    proposition: str = Field(description="The claim in plain language.")
    causal_chain: str = Field(
        description="How the claim says one factor produces or prevents the outcome."
    )
    assumption: str = Field(
        description="The one condition whose failure would break the causal_chain."
    )
    weakness: str = Field(
        description="The outcome a study could measure that would show the assumption failing."
    )
    counterclaim: str = Field(
        description="The opposing claim that follows from the weakness, in one sentence."
    )
    counter_queries: list[str] = Field(
        description="2 to 3 short search queries that look for evidence of the weakness.",
    )


class CounterVerdict(BaseModel):
    status: Literal["grounded", "predictive", "rejected"] = Field(
        description=(
            "grounded: a passage supports the weakness. "
            "predictive: no passage supports it, but it follows from the causal_chain and assumption. "
            "rejected: neither holds."
        ),
    )
    scope: str = Field(
        default="",
        description="The condition under which the weakness holds. Set only when grounded.",
    )
    grounding: list[str] = Field(
        default_factory=list,
        description="corpus_ids of the passages attesting the weakness. Set only when grounded.",
    )


class Counterclaim(BaseModel):
    decomposition: ClaimDecomposition
    verdict: CounterVerdict


ClaimType = Literal[
    "descriptive",
    "comparative",
    "associative",
    "causal",
    "predictive",
]


class StudyDesign(BaseModel):
    context: str = Field(
        description="The setting, population, task, or domain where the hypothesis applies."
    )
    exposure: str = Field(
        description="The main condition, intervention, or observed factor."
    )
    comparator: str = Field(
        description="The baseline or rival condition the exposure is compared against."
    )
    outcome: str = Field(
        description="The construct being evaluated; may be abstract when the measure makes it observable."
    )
    measure: str = Field(
        description="The observable metric that tests the outcome (e.g. expert-score agreement, "
        "self-preference rate, residual bias after perturbation); never an abstract construct "
        "(validity, trustworthiness, reliability, quality).",
    )


class Hypothesis(BaseModel):
    id: str = Field(default="", description="Leave empty. Assigned after generation.")
    claim_type: ClaimType = Field(
        description="descriptive (composition or pattern), comparative (one condition differs from "
        "another), associative (X relates to Y, no cause), causal (X changes Y through a "
        "mechanism), or predictive (X forecasts, classifies, or estimates Y).",
    )
    proposition: str = Field(
        description="The hypothesis as one clear, testable sentence in the claim_type's logical "
        "form: what changes, compared to what, on what measured outcome, with the predicted "
        "direction. Calibrate strength to the evidence: hedge unless the relation is established.",
    )
    causal_chain: str = Field(
        description="The mechanism or explanatory pathway as a compact sequence, A -> B -> C, "
        "naming the mediator or process. For a non-causal claim_type (associative, comparative, "
        "predictive), state that logic without claiming causation.",
    )
    study_design: StudyDesign
    warrant: str = Field(
        description="Why the causal_chain and evidence support the proposition; do not restate the "
        "proposition or causal_chain. When the adjudication names a competing account, why this "
        "pathway beats or refines that account.",
    )
    falsifier: str = Field(
        description="A concrete observed result, stated against the measure, that would negate the "
        "proposition.",
    )
    grounding: list[str] = Field(
        default_factory=list,
        description="corpus_ids supporting the mechanism, outcome, or pattern, copied verbatim. "
        "At least 1.",
    )
    contributing_agents: list[str] = Field(
        default_factory=list,
        description="agent_ids whose arguments this hypothesis draws on. At most 3.",
    )


class BestCandidate(BaseModel):
    candidate_id: str = Field(
        description="id of the chosen candidate, copied from Synthesis.hypotheses (e.g. 'H4')."
    )
    reason: str = Field(
        description="One sentence on why this hypothesis best addresses the central unresolved question.",
    )


class MetaReview(BaseModel):
    problem: str = Field(
        description="The central difficulty as a question: the setting, the difficulty within it, "
        "and why it matters.",
    )
    previous_work: str = Field(
        description="The prior approaches the debate surfaced: what each explains, its limitation, "
        "and what is resolved versus unresolved.",
    )
    reasoning: str = Field(
        description="One causal chain from the primary condition to the outcome, with the "
        "competing account named and answered.",
    )
    hypothesis: str = Field(
        description="The selected candidate as one sentence with one causal claim, a directional "
        "verb, and an explicit comparison (than / rather than / relative to); hedge the verb unless "
        "the evidence establishes the relation.",
    )
    best_id: str = Field(
        default="",
        description="id of the candidate in Synthesis.hypotheses this output was built around.",
    )


class Synthesis(BaseModel):
    phase: str = Field(
        default="synthesis", description="Phase that produced this output."
    )
    cycle: int = Field(default=1, description="Round number this covers.")
    hypotheses: list[Hypothesis] = Field(
        default_factory=list,
        description="Every distinct candidate the debate surfaced, unranked.",
    )
    best: BestCandidate | None = Field(
        default=None,
        description="The selected candidate's id and the reason it was chosen. Null until selected.",
    )
    meta_review: MetaReview | None = Field(
        default=None,
        description="The four-part researcher-facing output. Null until composed.",
    )


class BaselineAgentResponse(BaseModel):
    message: str = Field(
        description="A concise answer to the researcher's question in plain language."
    )
    rationale: str = Field(
        description="One to three sentences explaining how the evidence and persona lens support the answer."
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Corpus IDs from the supplied evidence that support the answer.",
    )


class BaselineMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    role: Literal["user", "agent"]
    content: str
    agent_id: AgentId | None = None
    rationale: str | None = None
    evidence: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class BaselineConversation(BaseModel):
    messages: list[BaselineMessage] = Field(default_factory=list)


class Cycle(BaseModel):
    cycle_id: str = Field(default_factory=lambda: uuid4().hex)
    cycle: int = 1
    focal_claim: str
    problem: str = ""
    agent_ids: list[AgentId]
    status: CycleStatus = "pending"
    steers: list[Steer] = Field(default_factory=list)
    turns: list[AgentTurn] = Field(default_factory=list)
    evidence: dict[AgentId, EvidenceSet] = Field(default_factory=dict)
    judge_evidence: dict[AgentId, EvidenceSet] = Field(default_factory=dict)
    counter: dict[AgentId, Counterclaim] = Field(default_factory=dict)
    counter_evidence: dict[AgentId, EvidenceSet] = Field(default_factory=dict)
    assessment: DebateAssessment | None = None
    adjudication: Adjudication | None = None
    synthesis: Synthesis | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Debate(BaseModel):
    debate_id: str = Field(default_factory=lambda: uuid4().hex)
    focal_claim: str
    agents: list[Persona]
    cycle: Cycle | None = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
