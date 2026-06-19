from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from mars.models.persona import PersonaAgent


AgentId = str

AgentPhase = Literal["proposal", "rebuttal", "refutation"]
JudgePhase = Literal["adjudication", "synthesis"]
DebateEvent = AgentPhase | JudgePhase
AgentAction = Literal["challenge", "support", "concede"]

SteerType = Literal["emphasize", "reframe"]
CycleStatus = Literal["pending", "running", "complete"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Steer(BaseModel):
    type: SteerType
    text: str
    agent_id: AgentId


class EvidenceSnippet(BaseModel):
    corpus_id: str = Field(description="S2 corpusId of the source paper — copied verbatim into grounding.")
    title: str = Field(default="", description="Source paper title, for display in prose.")
    section: str | None = Field(default=None, description="Section the excerpt came from (e.g. 'Conclusion').")
    text: str = Field(description="The excerpt, ~500 words.")
    score: float | None = Field(default=None, description="Snippet relevance score from the endpoint.")
    tier: Literal["primary", "secondary", "judge"] = Field(
        description="primary = agent's own cluster; secondary = beyond the cluster; judge = cross-examination.",
    )


class EvidenceSet(BaseModel):
    snippets: list[EvidenceSnippet] = Field(default_factory=list)


class ScoutQueries(BaseModel):
    primary: list[str] = Field(
        min_length=2, max_length=2,
        description="Two queries that find evidence to SHAPE this agent's argument, from its own "
        "cluster. Each one short descriptive sentence.",
    )
    secondary: str = Field(
        description="One query that finds evidence to AUGMENT the argument from beyond the cluster. "
        "One short descriptive sentence.",
    )


class SearchQuery(BaseModel):
    query: str = Field(description="One short descriptive sentence for semantic snippet search.")


class AgentResponse(BaseModel):
    claim: str = Field(description="Your position, as one contestable sentence.")
    rationale: str = Field(description="Why you hold it, grounded in your evidence.")
    evidence: list[str] = Field(
        default_factory=list,
        description="corpus_ids supporting this turn, copied verbatim from the Corpus ID "
        "lines in your evidence. Leave empty if no evidence was retrieved — never invent one.",
    )
    message: str = Field(description="Your spoken turn, in plain language.")
    action: AgentAction | None = Field(
        default=None,
        description="Your stance toward the target's claim. None when proposing.",
    )
    target_id: AgentId | None = Field(
        default=None,
        description="The agent you address. None when proposing.",
    )


class AgentTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: uuid4().hex)
    agent_id: AgentId
    phase: AgentPhase
    cycle: int = 1
    response: AgentResponse
    created_at: datetime = Field(default_factory=_utcnow)


class Stance(BaseModel):
    agent_id: str = Field(description="The agent whose position this is.")
    position: str = Field(
        description="The agent's core position on the focal claim, in one sentence — "
        "the side it stakes and its central reason. Not a summary of its whole perspective.",
    )


class Disagreement(BaseModel):
    agents: list[str] = Field(
        description="The agents on opposing sides of this clash (name at least two).",
    )
    point: str = Field(
        description="The precise proposition they disagree on — primacy, mechanism, "
        "sufficiency, definition, or scope. State the conflict directly, not a compromise.",
    )


class Critique(BaseModel):
    target: str = Field(description="The agent whose position carries this weakness.")
    challenger: str = Field(
        default="",
        description="The agent best placed to press it, or '' if any opponent could.",
    )
    on_point: str = Field(
        description="The specific weakness to challenge — an unsupported step, an "
        "overstated link, an unaddressed alternative. What to attack, not who is winning.",
    )


class DebateAssessment(BaseModel):
    phase: str = Field(default="assessment", description="The phase this assessment was produced in.")
    cycle: int = Field(default=1, description="The round number this assessment covers.")

    overview: str = Field(
        description="One short paragraph: where the debate stands after proposals. "
        "Orienting only — do not restate the fields below or favor a side.",
    )
    stances: list[Stance] = Field(
        default_factory=list,
        description="Each agent's staked position, one per participating agent.",
    )
    points_of_agreement: list[str] = Field(
        default_factory=list,
        description="Propositions two or more agents explicitly share — common ground the "
        "rebuttal round need not relitigate. Propositions, not shared topic framing.",
    )
    points_of_disagreement: list[Disagreement] = Field(
        default_factory=list,
        description="The live clashes after proposals, each naming the agents and the precise point.",
    )
    central_conflict: str = Field(
        description="The ONE disagreement the rebuttal round should fight over — the axis "
        "most central to the focal claim and still unresolved. The keystone of this assessment; "
        "the rebuttal round is organized around it.",
    )
    critiques: list[Critique] = Field(
        default_factory=list,
        description="The specific weaknesses the rebuttal round should pursue, as engagement "
        "directives (who challenges whom, on what). Fuel for rebuttals, not a judgment of who leads.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved threads raised in the proposals that further debate could settle. "
        "Drawn from the proposals only; introduce no new terminology.",
    )
    disagreement_present: bool = Field(
        default=True,
        description="True if the proposals genuinely stake opposing positions; False if they "
        "converged on one side. False is the consensus-collapse signal: the central_conflict is "
        "then strained or manufactured, and the debate has no real opposition to resolve.",
    )


class Adjudication(BaseModel):
    phase: str = Field(default="adjudication", description="The phase this was produced in.")
    cycle: int = Field(default=1, description="The round this covers.")

    reasoning: str = Field(
        description="The judge's chain of thought over the full transcript — how the "
        "exchange bore on the central conflict, step by step.",
    )
    resolved: list[str] = Field(
        default_factory=list,
        description="What the exchange settled — points the rebuttals and refinements closed.",
    )
    unresolved: list[str] = Field(
        default_factory=list,
        description="What remains contested after the cycle — the live, open disputes.",
    )


class HypothesisVariables(BaseModel):
    independent: str = Field(description="The IV — the cause being manipulated or contrasted.")
    dependent: str = Field(description="The DV — the measured effect, at the level the question asks.")
    moderators: list[str] = Field(
        default_factory=list,
        description="Conditions that change the strength or direction of the IV->DV link.",
    )
    mediators: list[str] = Field(
        default_factory=list,
        description="Intervening variables the causal chain runs through.",
    )


class Hypothesis(BaseModel):
    id: str = Field(default="", description="Leave empty; assigned after generation.")
    statement: str = Field(
        description="The hypothesis as ONE sentence. Form: '[mechanism/construct] affects "
        "[dependent variable] in [direction], strongest in [scope/moderator], holding [controls] "
        "constant.' Lead with the mechanism; name a specific method only as an example, never as "
        "the grammatical subject. The dependent variable must answer the question at the level "
        "asked — a 'what mechanism' question takes a mechanistic DV, not a downstream phenotype or "
        "proxy, and uses the same quantity the problem names.",
    )
    relationship: str = Field(description="IV->DV relationship: positive | negative | non-linear")
    mechanism: str = Field(
        description="The single causal chain from IV to DV — the 'because' (A changes B changes C). "
        "If something must be true but is NOT part of this chain, it belongs in assumptions, not here.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Standalone conditions that must hold for the mechanism to operate but that you "
        "are NOT testing. Aim for at most 4.",
    )
    variables: HypothesisVariables
    controls: list[str] = Field(
        default_factory=list,
        description="What is held constant to isolate the IV. Each control must be a DIFFERENT "
        "entity from the IV. Aim for at most 3.",
    )
    falsifier: str = Field(
        description="The direct negation of the statement's direction on its dependent variable. A "
        "concrete observed result, not a competing theory; introduce no new variable.",
    )
    scope: str = Field(description="The population/setting you would sample from. Not the same as moderators.")
    grounding: list[str] = Field(
        default_factory=list,
        description="Cited paper_ids supporting the mechanism, copied verbatim. At least one.",
    )
    contributing_agents: list[str] = Field(
        default_factory=list,
        description="The agents whose arguments fed this hypothesis. Aim for at most 3.",
    )


class BestCandidate(BaseModel):
    candidate_id: str = Field(description="id of the chosen candidate (e.g. 'H4').")
    reason: str = Field(
        description="One sentence: why this candidate is the debate's central unresolved claim.",
    )


class MetaReview(BaseModel):
    problem: str = Field(
        description="The central difficulty, posed as a question. The setting first, then the "
        "difficulty within it; concrete domain terms; why it matters if unresolved.",
    )
    previous_work: str = Field(
        description="The prior approaches the debate surfaced, what each explains and its specific "
        "limitation, what is settled vs contested, and what motivates the open question.",
    )
    reasoning: str = Field(
        description="One causal chain from the primary condition to the outcome, with the key step "
        "spelled out, the main rival named and answered, and any tentative link marked.",
    )
    hypothesis: str = Field(
        description="The selected candidate as ONE sentence (never one clause) with one main causal "
        "claim and a directional verb. Explicit comparison (than / rather than / relative to); the "
        "boundary condition integrated grammatically ('with the effect largest in ...'); any control "
        "stated as persistence ('persisting when ... is held constant'); an integrated theory tail "
        "('challenging accounts that ...') only when explanatory. No em-dash add-ons. The clearest "
        "sentence in the output.",
    )
    best_id: str = Field(
        default="",
        description="id of the candidate in Synthesis.hypotheses this output was built around.",
    )


class Synthesis(BaseModel):
    phase: str = Field(default="synthesis", description="The phase this was produced in.")
    cycle: int = Field(default=1, description="The round this covers.")
    hypotheses: list[Hypothesis] = Field(
        default_factory=list,
        description="Every distinct candidate the debate surfaced, unranked (from summarize).",
    )
    best: BestCandidate | None = Field(
        default=None,
        description="The selected candidate's id and the reason it was chosen (from select_best).",
    )
    meta_review: MetaReview | None = Field(
        default=None,
        description="The four-step researcher-facing output (from synthesize). None until composed.",
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
    assessment: DebateAssessment | None = None
    adjudication: Adjudication | None = None
    synthesis: Synthesis | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Debate(BaseModel):
    debate_id: str = Field(default_factory=lambda: uuid4().hex)
    focal_claim: str
    agents: list[PersonaAgent]
    cycle: Cycle | None = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
