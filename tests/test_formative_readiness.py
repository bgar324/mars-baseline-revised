import asyncio

from mars.models.persona import Persona
from mars.schemas.event import DebateRunRequest, StageName
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext
from mars.workflow.pipeline import Pipeline


def persona(cluster_id: int) -> Persona:
    return Persona(
        cluster_id=cluster_id,
        references=[],
        methods_summary="Methods",
        evidence_relation="direct",
        name=f"Researcher {cluster_id}",
        framing="Frame",
        background="Background",
        reasoning_style="mechanistic",
        evaluation_lens="internal_validity",
        instructions=["Argue from evidence.", "Stay scoped.", "Name limits."],
    )


def test_debate_request_accepts_full_personas() -> None:
    request = DebateRunRequest(personas=[persona(1), persona(2)])

    assert request.cluster_ids == []
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
    state = pipeline.create_query("How should teams evaluate AI tools?", "manual")

    payload = pipeline.export_session(
        state.query_id,
        frontend_snapshot={"personaEdits": {"1": {"name": "Edited"}}},
    )

    assert payload["query_id"] == state.query_id
    assert payload["mode"] == "manual"
    assert payload["research_problem"] == "How should teams evaluate AI tools?"
    assert "state" in payload
    assert "artifacts" in payload
    assert payload["frontend"]["personaEdits"]["1"]["name"] == "Edited"

