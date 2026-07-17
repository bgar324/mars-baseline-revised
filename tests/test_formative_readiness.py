import asyncio
from unittest.mock import AsyncMock, patch

from mars.api.router import create_query as create_query_endpoint
from mars.llm.providers.base import (
    LLMProvider,
    LLMResponse,
    ProviderType,
    StructuredResponse,
    TokenUsage,
)
from mars.models.debate import (
    BaselineAgentResponse,
    BaselineMessage,
    Cycle,
    Debate,
    EvidenceSet,
    EvidenceSnippet,
    MetaReview,
    Synthesis,
)
from mars.models.persona import Persona
from mars.models.s2 import Paper
from mars.schemas.debate import BaselineChatRequest
from mars.schemas.event import DebateRunRequest, QueryRequest, StageName
from mars.workflow.baseline import respond_to_researcher
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext
from mars.workflow.pipeline import Pipeline


def persona(cluster_id: int) -> Persona:
    return Persona(
        cluster_id=cluster_id,
        references=[],
        methods_summary="Methods",
        evidence_relation="direct",
        name=f"Researcher {cluster_id}",
        role="Research Methodologist",
        perspective="Focuses on evidence quality and testable research designs.",
        framing="Frame",
        background="Background",
        reasoning_style="mechanistic",
        evaluation_lens="internal_validity",
        instructions=["Argue from evidence.", "Stay scoped.", "Name limits."],
    )


def test_dedupe_roles_disambiguates_collisions() -> None:
    from mars.workflow.persona import dedupe_roles

    # Three researchers the model independently labelled the same role, plus
    # a case/whitespace variant that should also count as a collision.
    people = [persona(1), persona(2), persona(3), persona(4)]
    people[3].role = "  research   methodologist  "  # normalizes to a dupe

    result = dedupe_roles(people)

    roles = [p.role for p in sorted(result, key=lambda p: p.cluster_id)]
    # First occurrence keeps its label; every later collision is disambiguated.
    assert roles[0] == "Research Methodologist"
    assert all(role != "Research Methodologist" for role in roles[1:])
    # Uniqueness holds case- and whitespace-insensitively across the panel.
    assert len({r.casefold() for r in roles}) == len(roles)


def test_dedupe_roles_backfills_empty_role() -> None:
    from mars.workflow.persona import dedupe_roles

    person = persona(1)
    person.role = "   "
    (out,) = dedupe_roles([person])
    assert out.role == "Researcher"


def test_debate_request_accepts_full_personas() -> None:
    paper = Paper(id="paper-1", title="Selected source")
    request = DebateRunRequest(
        personas=[persona(1), persona(2)],
        papers=[paper],
    )

    assert request.cluster_ids == []
    assert request.papers == [paper]
    assert [p.name for p in request.personas] == ["Researcher 1", "Researcher 2"]


class FailingStep(BaseStep):
    name = "fail.step"

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        raise RuntimeError("planned failure")


class MarkerStep(BaseStep):
    name = "marker.step"

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        ctx.raw_text = "marker ran"
        return ctx


class FailingNode(BaseNode):
    def __init__(self) -> None:
        super().__init__(
            stage=StageName.EXTRACT,
            name="failing",
            steps=[FailingStep()],
        )


class MarkerNode(BaseNode):
    def __init__(self) -> None:
        super().__init__(
            stage=StageName.RETRIEVE,
            name="marker",
            steps=[MarkerStep()],
        )


def test_pipeline_stops_after_failed_stage() -> None:
    pipeline = Pipeline(nodes=[FailingNode(), MarkerNode()])
    state = pipeline.create_query("original")

    asyncio.run(pipeline.run_all(state.query_id))

    assert state.stages[StageName.EXTRACT].status == "failed"
    assert state.stages[StageName.RETRIEVE].status == "pending"
    assert pipeline.get_context(state.query_id).raw_text == "original"


def test_export_payload_contains_core_session_fields() -> None:
    pipeline = Pipeline(nodes=[])
    state = pipeline.create_query(
        "How should teams evaluate AI tools?", "manual", "baseline"
    )
    pipeline.get_context(state.query_id).baseline_messages.append(
        BaselineMessage(role="user", content="What would falsify this?")
    )

    payload = pipeline.export_session(
        state.query_id,
        frontend_snapshot={"personaEdits": {"1": {"name": "Edited"}}},
    )

    assert payload["query_id"] == state.query_id
    assert payload["schema_version"] == 1
    assert payload["condition"] == "baseline"
    assert payload["mode"] == "manual"
    assert payload["research_problem"] == "How should teams evaluate AI tools?"
    assert "state" in payload
    assert "artifacts" in payload
    assert payload["artifacts"]["baseline_messages"][0]["content"] == (
        "What would falsify this?"
    )
    assert payload["frontend"]["personaEdits"]["1"]["name"] == "Edited"


def test_query_request_defaults_to_mars_condition() -> None:
    assert QueryRequest(query="A question").condition == "mars"
    assert QueryRequest(query="A question", condition="baseline").condition == "baseline"


def test_baseline_query_starts_without_automatic_pipeline() -> None:
    pipeline = Pipeline(nodes=[MarkerNode()])
    request = QueryRequest(
        query="How does AI assistance affect scientific judgment?",
        mode="manual",
        condition="baseline",
    )

    with patch("mars.api.router._spawn") as spawn:
        state = asyncio.run(create_query_endpoint(request, pipeline))

    ctx = pipeline.get_context(state.query_id)
    spawn.assert_not_called()
    assert ctx.extracted is not None
    assert ctx.extracted.claim == request.query
    assert ctx.papers == []
    assert ctx.personas == []
    assert state.stages[StageName.RETRIEVE].status == "skipped"


class FakeChatProvider(LLMProvider):
    name = ProviderType.GEMINI

    async def generate(self, *, messages, thinking_level=None) -> LLMResponse:
        raise NotImplementedError

    async def generate_structured(self, *, messages, schema, **kwargs):
        assert schema is BaselineAgentResponse
        return StructuredResponse(
            parsed=BaselineAgentResponse(
                message="The result should be tested under distribution shift.",
                rationale="The supplied study reports a shift-sensitive effect.",
                evidence=["42", "invented"],
            ),
            usage=TokenUsage(),
            model="fake",
            provider=self.name,
        )

    async def create_cache(
        self, *, system_instruction: str, content: str, ttl_seconds: int = 3600
    ) -> str:
        raise NotImplementedError

    async def delete_cache(self, cache_name: str) -> None:
        raise NotImplementedError


def test_baseline_chat_persists_user_and_grounded_agent_messages() -> None:
    agent = persona(1)
    cycle = Cycle(
        focal_claim="The intervention improves transfer.",
        problem="When does the intervention improve transfer?",
        agent_ids=["1"],
        status="complete",
        synthesis=Synthesis(
            meta_review=MetaReview(
                problem="Transfer remains uncertain.",
                previous_work="Prior work reports mixed transfer.",
                reasoning="Distribution shift may moderate the effect.",
                hypothesis="The intervention may improve in-domain transfer.",
            )
        ),
        evidence={
            "1": EvidenceSet(
                snippets=[
                    EvidenceSnippet(
                        corpus_id="42",
                        title="A grounded study",
                        text="The effect changed under distribution shift.",
                        tier="primary",
                    )
                ]
            )
        },
    )
    ctx = WorkflowContext(
        query_id="q1",
        raw_text=cycle.problem,
        mode="manual",
        condition="baseline",
        personas=[agent],
        debate=Debate(focal_claim=cycle.focal_claim, agents=[agent], cycle=cycle),
        cycle=cycle,
    )

    conversation = asyncio.run(
        respond_to_researcher(
            ctx,
            BaselineChatRequest(message="How should we test it?", agent_ids=["1"]),
            FakeChatProvider(),
        )
    )

    assert [message.role for message in conversation.messages] == ["user", "agent"]
    assert conversation.messages[1].agent_id == "1"
    assert conversation.messages[1].evidence == ["42"]
    assert ctx.baseline_messages == conversation.messages


class DemoStep(BaseStep):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        return ctx


class DemoNode(BaseNode):
    def __init__(self, stage: StageName, steps: list[str]) -> None:
        super().__init__(
            stage=stage,
            name=f"demo-{stage.value}",
            steps=[DemoStep(name) for name in steps],
        )


def test_demo_pipeline_completes_without_external_providers() -> None:
    debate_steps = [
        "debate.prepare_evidence",
        "debate.proposal",
        "debate.assessment",
        "debate.rebuttal",
        "debate.refinement",
        "debate.adjudication",
        "debate.synthesis",
        "debate.select_best",
        "debate.compose",
    ]
    pipeline = Pipeline(
        nodes=[
            DemoNode(StageName.EXTRACT, ["extract.demo"]),
            DemoNode(StageName.RETRIEVE, ["retrieve.demo"]),
            DemoNode(StageName.CLUSTER, ["cluster.demo"]),
            DemoNode(StageName.PERSONA, ["persona.demo"]),
            DemoNode(StageName.DEBATE, debate_steps),
        ]
    )
    state = pipeline.create_query(
        "Does AI-assisted writing change evaluation skill?",
        "manual",
        "baseline",
        True,
    )

    with patch("mars.workflow.pipeline.asyncio.sleep", new=AsyncMock()):
        asyncio.run(pipeline.run_demo_setup(state.query_id))
        asyncio.run(pipeline.run_demo_debate(state.query_id))

    ctx = pipeline.get_context(state.query_id)
    assert ctx.test_mode is True
    assert len(ctx.personas) == 4
    assert [persona.name for persona in ctx.personas] == [
        "Aster",
        "Lyra",
        "Atlas",
        "Mira",
    ]
    assert all(persona.role and persona.perspective for persona in ctx.personas)
    assert state.stages[StageName.DEBATE].status == "complete"
    assert ctx.cycle is not None and ctx.cycle.synthesis is not None
    assert ctx.cycle.synthesis.meta_review is not None
    assert ctx.cycle.synthesis.meta_review.best_id == "H1"
