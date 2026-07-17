import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loguru import logger as _logger

from mars.client.s2 import SemanticScholarClient
from mars.config.pipeline import ClusterConfig, RetrievalConfig
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.llm.providers.usage import UsageTracker
from mars.logging.format import (
    format_duration,
    format_failure_duration,
    format_model,
    format_token_usage,
    join_meta,
)
from mars.llm.providers.langextract import LangExtractProvider
from mars.schemas.event import (
    STAGE_EVENT,
    EventType,
    PipelineEvent,
    PipelineState,
    StageName,
    StageNode,
    StageStatus,
    StepNode,
    StepStatus,
)
from mars.schemas.query import ExtractedQuery
from mars.workflow.base import BaseNode, WorkflowContext
from mars.workflow.cluster import ClusterNode
from mars.workflow.debate import DebateNode, DebateNodeConfig
from mars.workflow.persona import PersonaNode, PersonaNodeConfig
from mars.workflow.query import QueryNode, QueryNodeConfig
from mars.workflow.retrieval import RetrievalNode

if TYPE_CHECKING:
    from mars.db.study import StudySessionRecorder


class PipelineError(Exception): ...


class NotFoundError(PipelineError): ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _add_usage(target: TokenUsage | None, src: TokenUsage) -> TokenUsage:
    out = target or TokenUsage()
    out.input_tokens += src.input_tokens
    out.output_tokens += src.output_tokens
    out.thinking_tokens += src.thinking_tokens
    out.cached_tokens += src.cached_tokens
    out.total_tokens += src.total_tokens
    return out


class _StepTrace:
    def __init__(self, pipeline, query_id, node, stage_node, slog):
        self._p = pipeline
        self._qid = query_id
        self._node = node
        self._sn = stage_node
        self._log = slog

    async def on_step_start(self, step, event):
        sn = self._sn.steps[step]
        sn.status = StepStatus.RUNNING
        sn.started_at = _now()
        sn.error = None
        self._p._touch(self._qid)
        self._log.debug("{} | started", event)
        await self._p._emit(
            self._qid,
            PipelineEvent(
                event=EventType.STEP_STARTED,
                query_id=self._qid,
                stage=self._node.stage,
                step=step,
                timestamp=_now(),
            ),
        )

    async def on_step_skip(self, step):
        sn = self._sn.steps[step]
        sn.status = StepStatus.SKIPPED
        sn.completed_at = _now()
        self._p._touch(self._qid)
        await self._p._emit(
            self._qid,
            PipelineEvent(
                event=EventType.STEP_SKIPPED,
                query_id=self._qid,
                stage=self._node.stage,
                step=step,
                timestamp=_now(),
            ),
        )

    async def on_step_complete(self, step, event, summary, result_msg, duration, call):
        sn = self._sn.steps[step]
        sn.status = StepStatus.COMPLETE
        sn.completed_at = _now()
        sn.result = summary
        sn.duration_seconds = duration
        sn.usage = call.usage
        self._sn.usage = _add_usage(self._sn.usage, call.usage)
        self._p._touch(self._qid)

        self._log.info(
            "{} | {}",
            event,
            join_meta(
                format_duration(duration),
                format_token_usage(call.usage),
                format_model(call.provider, call.model),
            ),
        )
        if result_msg:
            self._log.info("result | {}", result_msg)

        await self._p._emit(
            self._qid,
            PipelineEvent(
                event=EventType.STEP_COMPLETED,
                query_id=self._qid,
                stage=self._node.stage,
                step=step,
                payload=summary,
                timestamp=_now(),
            ),
        )

    async def on_step_error(self, step, event, exc, duration, call):
        sn = self._sn.steps[step]
        sn.status = StepStatus.FAILED
        sn.error = str(exc)
        sn.completed_at = _now()
        sn.duration_seconds = duration
        sn.usage = call.usage
        self._sn.usage = _add_usage(self._sn.usage, call.usage)
        self._p._touch(self._qid)
        await self._p._emit(
            self._qid,
            PipelineEvent(
                event=EventType.STEP_FAILED,
                query_id=self._qid,
                stage=self._node.stage,
                step=step,
                payload={"error": str(exc)},
                timestamp=_now(),
            ),
        )


def _dump(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _dump(v) for k, v in value.items()}
    return value


def _dump_paper(paper) -> dict[str, Any]:
    data = paper.model_dump(mode="json")
    data.pop("specter_v2", None)
    return data


class Pipeline:
    def __init__(
        self,
        *,
        nodes: list[BaseNode],
        recorder: "StudySessionRecorder | None" = None,
    ) -> None:
        self._nodes = nodes
        self._order = [n.stage for n in nodes]
        self._states: dict[str, PipelineState] = {}
        self._contexts: dict[str, WorkflowContext] = {}
        self._subscribers: dict[str, set[asyncio.Queue[PipelineEvent]]] = {}
        self._recorder = recorder

    def create_query(
        self,
        text: str,
        mode: str = "auto",
        condition: str = "mars",
        test_mode: bool = False,
    ) -> PipelineState:
        query_id = uuid4().hex
        now = _now()
        stages: dict[StageName, StageNode] = {}
        for node in self._nodes:
            steps = {s.name: StepNode(name=s.name) for s in node.steps}
            stages[node.stage] = StageNode(
                stage=node.stage, status=StageStatus.PENDING, steps=steps
            )
        self._states[query_id] = PipelineState(
            query_id=query_id, stages=stages, created_at=now, updated_at=now
        )
        self._contexts[query_id] = WorkflowContext(
            query_id=query_id,
            raw_text=text,
            mode=mode,
            condition=condition,
            test_mode=test_mode,
        )
        if condition == "baseline":
            self._contexts[query_id].extracted = ExtractedQuery(
                raw_text=text,
                spans=[],
                claim=text,
            )
            for stage, stage_node in stages.items():
                if stage != StageName.DEBATE:
                    stage_node.status = StageStatus.SKIPPED
                    stage_node.completed_at = now
        self._subscribers.setdefault(query_id, set())
        return self._states[query_id]

    async def run_demo_setup(self, query_id: str) -> PipelineState:
        from mars.workflow.demo import DEMO_SETUP_STEP_DELAYS, populate_setup_stage

        state = self._require(query_id)
        ctx = self._contexts[query_id]
        for stage in (
            StageName.EXTRACT,
            StageName.RETRIEVE,
            StageName.CLUSTER,
            StageName.PERSONA,
        ):
            stage_node = state.stages[stage]
            stage_node.status = StageStatus.RUNNING
            stage_node.started_at = _now()
            self._touch(query_id)
            await self._emit(
                query_id,
                PipelineEvent(
                    event=EventType.STAGE_STARTED,
                    query_id=query_id,
                    stage=stage,
                    timestamp=_now(),
                ),
            )
            for step_name, step_node in stage_node.steps.items():
                step_node.status = StepStatus.RUNNING
                step_node.started_at = _now()
                self._touch(query_id)
                await self._emit(
                    query_id,
                    PipelineEvent(
                        event=EventType.STEP_STARTED,
                        query_id=query_id,
                        stage=stage,
                        step=step_name,
                        payload={"test_mode": True},
                        timestamp=_now(),
                    ),
                )
                await asyncio.sleep(DEMO_SETUP_STEP_DELAYS.get(step_name, 2.0))
                step_node.status = StepStatus.COMPLETE
                step_node.completed_at = _now()
                self._touch(query_id)
                await self._emit(
                    query_id,
                    PipelineEvent(
                        event=EventType.STEP_COMPLETED,
                        query_id=query_id,
                        stage=stage,
                        step=step_name,
                        payload={"test_mode": True},
                        timestamp=_now(),
                    ),
                )
            populate_setup_stage(ctx, stage)
            stage_node.status = StageStatus.COMPLETE
            stage_node.completed_at = _now()
            self._touch(query_id)
            await self._emit(
                query_id,
                PipelineEvent(
                    event=STAGE_EVENT[stage],
                    query_id=query_id,
                    stage=stage,
                    payload={"test_mode": True},
                    timestamp=_now(),
                ),
            )
            await self.persist_session(query_id)
        return state

    async def run_demo_debate(self, query_id: str) -> PipelineState:
        from mars.workflow.demo import (
            DEMO_DEBATE_DELAYS,
            initialize_demo_debate,
            populate_debate_step,
        )

        state = self._require(query_id)
        ctx = self._contexts[query_id]
        stage_node = state.stages[StageName.DEBATE]
        initialize_demo_debate(ctx)
        stage_node.status = StageStatus.RUNNING
        stage_node.started_at = _now()
        stage_node.error = None
        self._touch(query_id)
        await self._emit(
            query_id,
            PipelineEvent(
                event=EventType.STAGE_STARTED,
                query_id=query_id,
                stage=StageName.DEBATE,
                timestamp=_now(),
            ),
        )

        for step_name, step_node in stage_node.steps.items():
            step_node.status = StepStatus.RUNNING
            step_node.started_at = _now()
            await self._emit(
                query_id,
                PipelineEvent(
                    event=EventType.STEP_STARTED,
                    query_id=query_id,
                    stage=StageName.DEBATE,
                    step=step_name,
                    payload={"test_mode": True},
                    timestamp=_now(),
                ),
            )
            await asyncio.sleep(DEMO_DEBATE_DELAYS[step_name])
            populate_debate_step(ctx, step_name)
            step_node.status = StepStatus.COMPLETE
            step_node.completed_at = _now()
            self._touch(query_id)
            await self._emit(
                query_id,
                PipelineEvent(
                    event=EventType.STEP_COMPLETED,
                    query_id=query_id,
                    stage=StageName.DEBATE,
                    step=step_name,
                    payload={"test_mode": True},
                    timestamp=_now(),
                ),
            )

        if ctx.cycle is not None:
            ctx.cycle.status = "complete"
        if ctx.debate is not None and ctx.cycle is not None and ctx.cycle.synthesis:
            ctx.debate.hypotheses = list(ctx.cycle.synthesis.hypotheses)
        stage_node.status = StageStatus.COMPLETE
        stage_node.completed_at = _now()
        stage_node.result = {
            "turns": len(ctx.cycle.turns) if ctx.cycle else 0,
            "hypotheses": len(ctx.cycle.synthesis.hypotheses)
            if ctx.cycle and ctx.cycle.synthesis
            else 0,
            "test_mode": True,
        }
        self._touch(query_id)
        await self._emit(
            query_id,
            PipelineEvent(
                event=EventType.STAGE_COMPLETED,
                query_id=query_id,
                stage=StageName.DEBATE,
                payload=stage_node.result,
                timestamp=_now(),
            ),
        )
        await self.persist_session(query_id)
        return state

    async def run_all(
        self, query_id: str, *, stop_before: StageName | None = None
    ) -> PipelineState:
        state = self._require(query_id)
        for node in self._nodes:
            if stop_before is not None and node.stage == stop_before:
                break
            await self._run_node(query_id, node)
            if state.stages[node.stage].status is StageStatus.FAILED:
                break

        done = sum(1 for s in state.stages.values() if s.status is StageStatus.COMPLETE)
        total_usage = TokenUsage()
        total_secs = 0.0
        for s in state.stages.values():
            if s.usage:
                total_usage = _add_usage(total_usage, s.usage)
            total_secs += s.duration_seconds or 0.0
        _logger.bind(source="workflow.pipeline", stage="pipeline").info(
            "run.completed | {} | {}",
            f"completed {done}/{len(self._order)} stages in {total_secs:.1f}s",
            format_token_usage(total_usage),
        )
        return state

    async def run_stage(self, query_id: str, stage: StageName) -> PipelineState:
        state = self._require(query_id)
        node = next((n for n in self._nodes if n.stage == stage), None)
        if node is None:
            raise NotFoundError(f"stage '{stage}' not found")
        await self._run_node(query_id, node)
        return state

    def get_state(self, query_id: str) -> PipelineState:
        return self._require(query_id)

    def get_context(self, query_id: str) -> WorkflowContext:
        self._require(query_id)
        return self._contexts[query_id]

    async def subscribe(self, query_id: str) -> AsyncIterator[PipelineEvent]:
        self._require(query_id)
        queue: asyncio.Queue[PipelineEvent] = asyncio.Queue()
        self._subscribers.setdefault(query_id, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.get(query_id, set()).discard(queue)

    def _require(self, query_id: str) -> PipelineState:
        state = self._states.get(query_id)
        if state is None:
            raise NotFoundError(f"query '{query_id}' not found")
        return state

    def _touch(self, query_id: str) -> None:
        self._states[query_id].updated_at = _now()

    async def _emit(self, query_id: str, event: PipelineEvent) -> None:
        for queue in list(self._subscribers.get(query_id, ())):
            await queue.put(event)
        if self._recorder is not None:
            await self._recorder.record_event(event)

    def _make_emitter(self, query_id: str):
        async def emit(
            event: EventType,
            *,
            stage: StageName | None = None,
            step: str | None = None,
            payload: Any = None,
        ) -> None:
            await self._emit(
                query_id,
                PipelineEvent(
                    event=event,
                    query_id=query_id,
                    stage=stage,
                    step=step,
                    payload=payload,
                    timestamp=_now(),
                ),
            )

        return emit

    def export_session(
        self,
        query_id: str,
        *,
        frontend_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = self._require(query_id)
        ctx = self._contexts[query_id]
        return {
            "schema_version": 1,
            "query_id": query_id,
            "condition": ctx.condition,
            "test_mode": ctx.test_mode,
            "mode": ctx.mode,
            "research_problem": ctx.raw_text,
            "state": state.model_dump(mode="json"),
            "artifacts": {
                "extracted": _dump(ctx.extracted),
                "expansion": _dump(ctx.expansion),
                "questions": _dump(ctx.questions),
                "anchors": _dump(ctx.anchors),
                "papers": [_dump_paper(p) for p in ctx.papers],
                "retrieval_diagnostics": ctx.retrieval_diagnostics or [],
                "clusters": {
                    str(cid): [p.id for p in papers]
                    for cid, papers in (ctx.clusters or {}).items()
                },
                "perspectives": ctx.perspectives or [],
                "personas": _dump(ctx.personas),
                "persona_pool": _dump(ctx.persona_pool),
                "debate": _dump(ctx.debate),
                "cycle": _dump(ctx.cycle),
                "synthesis": _dump(ctx.cycle.synthesis)
                if ctx.cycle is not None
                else None,
                "baseline_messages": _dump(ctx.baseline_messages),
            },
            "frontend": frontend_snapshot or {},
            "exported_at": _now().isoformat(),
        }

    async def persist_session(
        self,
        query_id: str,
        *,
        frontend_snapshot: dict[str, Any] | None = None,
        export_payload: dict[str, Any] | None = None,
        wait: bool = False,
    ) -> None:
        if self._recorder is None:
            return
        state = self._require(query_id)
        ctx = self._contexts[query_id]
        await self._recorder.upsert_session(
            state=state,
            ctx=ctx,
            backend_snapshot=self.export_session(query_id),
            frontend_snapshot=frontend_snapshot,
            export_payload=export_payload,
            wait=wait,
        )

    async def _run_node(self, query_id: str, node: BaseNode) -> None:
        state = self._states[query_id]
        ctx = self._contexts[query_id]
        stage_node = state.stages[node.stage]

        index = self._order.index(node.stage) + 1
        total = len(self._order)
        slog = _logger.bind(
            source=f"workflow.{node.stage.value}", stage=node.stage.value
        )

        if not node.enabled:
            stage_node.status = StageStatus.SKIPPED
            stage_node.completed_at = _now()
            self._touch(query_id)
            slog.info("stage.skipped | disabled by config")
            await self._emit(
                query_id,
                PipelineEvent(
                    event=EventType.STAGE_SKIPPED,
                    query_id=query_id,
                    stage=node.stage,
                    timestamp=_now(),
                ),
            )
            await self.persist_session(query_id)
            return

        stage_node.status = StageStatus.RUNNING
        stage_node.started_at = _now()
        stage_node.error = None
        self._touch(query_id)
        slog.info("stage.started | running ({}/{})", index, total)
        await self._emit(
            query_id,
            PipelineEvent(
                event=EventType.STAGE_STARTED,
                query_id=query_id,
                stage=node.stage,
                timestamp=_now(),
            ),
        )
        await self.persist_session(query_id)

        observer = _StepTrace(self, query_id, node, stage_node, slog)
        ctx.emit = self._make_emitter(query_id)
        started = perf_counter()
        try:
            ctx = await node.run(ctx, observer=observer)
        except Exception as exc:
            stage_node.duration_seconds = perf_counter() - started
            stage_node.status = StageStatus.FAILED
            stage_node.error = str(exc)
            stage_node.completed_at = _now()
            for sn in stage_node.steps.values():
                if sn.status is StepStatus.RUNNING:
                    sn.status = StepStatus.FAILED
                    sn.error = str(exc)
                    sn.completed_at = _now()
            self._contexts[query_id] = ctx
            self._touch(query_id)
            slog.opt(exception=True).error(
                "stage.failed | {}",
                join_meta(
                    format_failure_duration(stage_node.duration_seconds),
                    f"error: {exc}",
                ),
            )
            await self._emit(
                query_id,
                PipelineEvent(
                    event=EventType.STAGE_FAILED,
                    query_id=query_id,
                    stage=node.stage,
                    payload={"error": str(exc)},
                    timestamp=_now(),
                ),
            )
            await self.persist_session(query_id)
            return

        stage_node.duration_seconds = perf_counter() - started
        self._contexts[query_id] = ctx
        stage_node.status = StageStatus.COMPLETE
        stage_node.completed_at = _now()
        stage_node.result = node.summarize(ctx)
        self._touch(query_id)
        await self._emit(
            query_id,
            PipelineEvent(
                event=STAGE_EVENT.get(node.stage, EventType.STAGE_COMPLETED),
                query_id=query_id,
                stage=node.stage,
                payload=stage_node.result,
                timestamp=_now(),
            ),
        )
        await self.persist_session(query_id)


class Preset(str, Enum):
    FULL = "full"
    NO_DEBATE = "no_debate"
    NO_DEBATE_RETRIEVAL = "no_debate_retrieval"
    GENERIC_PERSONAS = "generic_personas"


def preset_configs(preset: Preset):
    persona = PersonaNodeConfig(grounded=preset is not Preset.GENERIC_PERSONAS)
    if preset is Preset.NO_DEBATE:
        debate = DebateNodeConfig(
            assessment=False, rebuttal=False, refinement=False, adjudication=False
        )
    elif preset is Preset.NO_DEBATE_RETRIEVAL:
        debate = DebateNodeConfig(debate_retrieval=False)
    else:
        debate = DebateNodeConfig()
    return None, None, None, persona, debate


def build(
    *,
    langextract: LangExtractProvider,
    gemini: LLMProvider,
    s2: SemanticScholarClient,
    query_config: QueryNodeConfig | None = None,
    retrieval_config: RetrievalConfig | None = None,
    cluster_config: ClusterConfig | None = None,
    persona_config: PersonaNodeConfig | None = None,
    debate_config: DebateNodeConfig | None = None,
    include_debate: bool = False,
    judge_llm: LLMProvider | None = None,
    retrieval_filters: dict | None = None,
    preset: Preset | None = None,
    recorder: "StudySessionRecorder | None" = None,
) -> Pipeline:
    if preset is not None:
        q, r, c, p, d = preset_configs(preset)
        query_config = query_config or q
        retrieval_config = retrieval_config or r
        cluster_config = cluster_config or c
        persona_config = persona_config or p
        debate_config = debate_config or d
        if preset in (Preset.NO_DEBATE, Preset.NO_DEBATE_RETRIEVAL):
            include_debate = True

    gemini = UsageTracker(gemini)
    judge_llm = UsageTracker(judge_llm) if judge_llm is not None else None

    nodes: list[BaseNode] = [
        QueryNode(langextract=langextract, gemini=gemini, config=query_config),
        RetrievalNode(s2=s2, config=retrieval_config),
        ClusterNode(config=cluster_config),
        PersonaNode(gemini=gemini, config=persona_config),
    ]
    if include_debate:
        nodes.append(
            DebateNode(
                llm=gemini,
                s2=s2,
                judge_llm=judge_llm,
                retrieval_filters=retrieval_filters,
                config=debate_config,
            )
        )

    for node in nodes:
        node.validate()

    return Pipeline(nodes=nodes, recorder=recorder)
