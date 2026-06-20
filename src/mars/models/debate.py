from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from mars.models.persona import Persona


AgentId = str

AgentPhase = Literal["proposal", "rebuttal", "refutation"]
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
        description="Section name the excerpt came from, e.g. 'Conclusion'.",
    )
    text: str = Field(description="The excerpt text, about 500 words.")
    score: float | None = Field(
        default=None,
        description="Snippet relevance score returned by the retrieval endpoint.",
    )
    tier: Literal[
        "primary",
        "secondary",
        "judge",
        "relation",
        "counter_internal",
        "counter_external",
    ] = Field(description="Retrieval stage that produced this snippet.")


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
        description="Set on rebuttal and refutation turns only. How the opponent's cited evidence "
        "bears on your position: strengthens, weakens, refines, disputed, or unrelated. Null on a "
        "proposal turn.",
    )
    claim: str = Field(description="Your position, as one contestable sentence.")
    rationale: str = Field(
        description="One to three sentences justifying the claim from your evidence."
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="corpus_ids supporting this turn, copied verbatim from the Corpus ID lines in "
        "your evidence. Leave empty if no evidence was retrieved; never invent an id.",
    )
    conceded_point: str | None = Field(
        default=None,
        description="Set only when evidence_weight is weakens: the specific part of your position "
        "the evidence undermines. Null otherwise.",
    )
    preserved_point: str | None = Field(
        default=None,
        description="Optional, only when evidence_weight is weakens: the part of your position that "
        "still holds. Null otherwise.",
    )
    revised_position: str | None = Field(
        default=None,
        description="Set only when evidence_weight is weakens: your position restated after the "
        "concession, in one sentence. Null otherwise.",
    )
    target_id: AgentId | None = Field(
        default=None,
        description="agent_id of the agent you address. Null on a proposal turn.",
    )
    message: str = Field(description="Your spoken turn in plain language.")
    action: TurnAction | None = Field(
        default=None,
        description="Leave null. Derived in code from evidence_weight; not chosen by the model.",
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
        description="The agent's core position on the focal claim in one sentence: the side it "
        "stakes and its central reason. Not a summary of its whole perspective.",
    )


class Disagreement(BaseModel):
    agents: list[str] = Field(
        description="agent_ids on opposing sides of this clash. At least 2.",
    )
    point: str = Field(
        description="The precise proposition they disagree on, covering primacy, mechanism, "
        "sufficiency, definition, or scope. State the conflict directly, not a compromise.",
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
        description="The specific weakness to challenge: an unsupported step, an overstated link, "
        "or an unaddressed alternative. What to attack, not who is winning.",
    )


class DebateAssessment(BaseModel):
    phase: str = Field(
        default="assessment", description="Phase that produced this assessment."
    )
    cycle: int = Field(default=1, description="Round number this assessment covers.")

    overview: str = Field(
        description="One short paragraph stating where the debate stands after the proposals. "
        "Orient only; do not restate the fields below or favor a side.",
    )
    stances: list[Stance] = Field(
        default_factory=list,
        description="One staked position per participating agent.",
    )
    points_of_agreement: list[str] = Field(
        default_factory=list,
        description="Propositions two or more agents explicitly share. Each is a proposition, not "
        "a shared topic framing.",
    )
    points_of_disagreement: list[Disagreement] = Field(
        default_factory=list,
        description="The live clashes after the proposals, each naming the agents and the precise "
        "point.",
    )
    central_conflict: str = Field(
        description="The single disagreement the rebuttal round must fight over: the axis most "
        "central to the focal claim that is still unresolved. The rebuttal round is organized "
        "around it.",
    )
    critiques: list[Critique] = Field(
        default_factory=list,
        description="The specific weaknesses the rebuttal round should pursue, as engagement "
        "directives stating who challenges whom on what. Not a judgment of who leads.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved threads raised in the proposals that further debate could settle. "
        "Draw only from the proposals; introduce no new terminology.",
    )
    disagreement_present: bool = Field(
        default=True,
        description="True if the proposals stake genuinely opposing positions; False if they "
        "converged on one side. False signals consensus collapse: central_conflict is then strained "
        "or manufactured and there is no real opposition to resolve.",
    )


class Adjudication(BaseModel):
    phase: str = Field(
        default="adjudication", description="Phase that produced this output."
    )
    cycle: int = Field(default=1, description="Round number this covers.")

    reasoning: str = Field(
        description="4 to 7 sentences on how the debate changed the central conflict, using two "
        "descriptive view labels derived from the conflict and tied back to the focal claim. "
        "Subject-matter terms only: no raw paper ids, no agent names, no 'Position A/B'.",
    )
    resolved: list[str] = Field(
        default_factory=list,
        description="Settled subject-matter propositions, each stating the condition or scope where "
        "it holds. No raw paper ids, no agent names.",
    )
    unresolved: list[str] = Field(
        default_factory=list,
        description="Open research-level questions, each naming the disputed mechanism and the "
        "comparison, condition, or threshold that would decide it. No raw paper ids, no agent "
        "names, no 'more research is needed'.",
    )


class ClaimDecomposition(BaseModel):
    claim: str = Field(description="The agent's claim being tested, in one sentence.")
    mechanism: str = Field(
        description="The causal process by which the claim says one factor produces or prevents an "
        "outcome."
    )
    assumption: str = Field(
        description="The one condition that must hold for the mechanism to support the claim, whose "
        "failure would break the mechanism."
    )
    weakness: str = Field(
        description="The point where the claim fails if the assumption does not hold. State it as "
        "something a paper could measure or observe."
    )
    counterclaim: str = Field(
        description="The revised or opposing claim that follows from the weakness, in one sentence."
    )
    counter_queries: list[str] = Field(
        description="2 to 3 search queries that find evidence of the weakness. Each names the "
        "mechanism and one failure mode, as one descriptive sentence for semantic snippet search.",
    )


class CounterVerdict(BaseModel):
    status: Literal["grounded", "predictive", "rejected"] = Field(
        description="grounded: a retrieved passage attests the weakness, so it can weaken the claim. "
        "predictive: no passage, but the weakness follows from the mechanism and assumption, so it "
        "is an open question. rejected: neither holds, so the weakness is dropped.",
    )
    scope: str = Field(
        default="",
        description="The condition under which the weakness holds. Set only when status is grounded.",
    )
    grounding: list[str] = Field(
        default_factory=list,
        description="corpus_ids of the passages attesting the weakness. Set only when status is "
        "grounded.",
    )


class Counterclaim(BaseModel):
    decomposition: ClaimDecomposition
    verdict: CounterVerdict


class HypothesisVariables(BaseModel):
    independent: str = Field(
        description="The independent variable: the cause being manipulated or contrasted."
    )
    dependent: str = Field(
        description="The dependent variable: the measured effect, at the level the question asks."
    )
    moderators: list[str] = Field(
        default_factory=list,
        description="Conditions that change the strength or direction of the IV-to-DV link.",
    )
    mediators: list[str] = Field(
        default_factory=list,
        description="Intervening variables the causal chain runs through.",
    )


class Hypothesis(BaseModel):
    id: str = Field(default="", description="Leave empty. Assigned after generation.")
    statement: str = Field(
        description="The hypothesis as one sentence, of the form '[mechanism/construct] affects "
        "[dependent variable] in [direction], strongest in [scope/moderator], holding [controls] "
        "constant.' Lead with the mechanism; name a specific method only as an example, never as the "
        "grammatical subject. The dependent variable must answer the question at the level asked: a "
        "'what mechanism' question takes a mechanistic DV, not a downstream phenotype or proxy, and "
        "uses the same quantity the problem names.",
    )
    relationship: str = Field(
        description="Direction of the IV-to-DV relationship: positive, negative, or non-linear."
    )
    is_relational: bool = Field(
        default=False,
        description="True only if this hypothesis states a relation between two mechanisms "
        "(ordering, threshold, interaction, moderator, trade-off, or primacy). False for a "
        "single-mechanism hypothesis.",
    )
    mechanism: str = Field(
        description="The single causal chain from IV to DV, the 'because' (A changes B changes C). "
        "Anything that must be true but is not part of this chain belongs in assumptions.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Standalone conditions that must hold for the mechanism to operate but that you "
        "are not testing. At most 4.",
    )
    variables: HypothesisVariables
    controls: list[str] = Field(
        default_factory=list,
        description="What is held constant to isolate the IV. Each control must be a different "
        "entity from the IV. At most 3.",
    )
    falsifier: str = Field(
        description="The direct negation of the statement's direction on its dependent variable, as "
        "a concrete observed result, not a competing theory. Introduce no new variable.",
    )
    scope: str = Field(
        description="The population or setting you would sample from. Distinct from moderators."
    )
    grounding: list[str] = Field(
        default_factory=list,
        description="corpus_ids supporting the mechanism, copied verbatim. At least 1.",
    )
    relation_grounding: list[str] = Field(
        default_factory=list,
        description="For relational hypotheses only: corpus_ids whose passages bear on the "
        "interaction itself, not on each mechanism separately. Empty means the relation is untested.",
    )
    contributing_agents: list[str] = Field(
        default_factory=list,
        description="agent_ids whose arguments fed this hypothesis. At most 3.",
    )


class BestCandidate(BaseModel):
    candidate_id: str = Field(
        description="id of the chosen candidate, copied from Synthesis.hypotheses (e.g. 'H4')."
    )
    reason: str = Field(
        description="One sentence stating why this candidate is the debate's central unresolved claim.",
    )


class MetaReview(BaseModel):
    problem: str = Field(
        description="The central difficulty posed as a question: state the setting first, then the "
        "difficulty within it, in concrete domain terms, and why it matters if unresolved.",
    )
    previous_work: str = Field(
        description="The prior approaches the debate surfaced: what each explains and its specific "
        "limitation, what is settled versus contested, and what motivates the open question.",
    )
    reasoning: str = Field(
        description="One causal chain from the primary condition to the outcome, with the key step "
        "spelled out, the main rival named and answered, and any tentative link marked as tentative.",
    )
    hypothesis: str = Field(
        description="The selected candidate as one sentence (never a single clause) with one main "
        "causal claim and a directional verb. Include an explicit comparison (than / rather than / "
        "relative to); integrate the boundary condition grammatically ('with the effect largest in "
        "...'); state any control as persistence ('persisting when ... is held constant'); add an "
        "integrated theory tail ('challenging accounts that ...') only when explanatory. No em-dash "
        "add-ons.",
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
