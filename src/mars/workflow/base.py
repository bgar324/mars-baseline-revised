from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from loguru import logger

from mars.llm.providers.usage import CallRecord, begin_step, end_step
from mars.models.debate import Cycle, Debate
from mars.models.persona import Persona
from mars.models.s2 import Paper
from mars.schemas.event import StageName
from mars.schemas.query import (
    ExtractedQuery,
    HypotheticalQuestions,
    QueryExpansion,
    RetrievalAnchors,
)


@dataclass
class WorkflowContext:
    query_id: str
    raw_text: str
    extracted: ExtractedQuery | None = None
    expansion: QueryExpansion | None = None
    questions: HypotheticalQuestions | None = None
    anchors: RetrievalAnchors | None = None
    papers: list[Paper] = field(default_factory=list)
    retrieval_diagnostics: list[dict[str, Any]] | None = None
    clusters: dict[int, list[Paper]] | None = None
    perspectives: list[int] | None = None
    personas: list[Persona] = field(default_factory=list)
    persona_pool: list[Persona] | None = None
    debate: Debate | None = None
    cycle: Cycle | None = None

    def require_extracted_query(self) -> ExtractedQuery:
        if self.extracted is None:
            raise MissingArtifactError("missing artifact: extracted")
        return self.extracted

    def require_persona_pool(self) -> list[Persona]:
        if self.persona_pool is None:
            raise MissingArtifactError("missing artifact: persona_pool")
        return self.persona_pool


class WorkflowError(Exception): ...


class MissingArtifactError(WorkflowError): ...


class ConfigError(WorkflowError): ...


class StepObserver(Protocol):
    async def on_step_start(self, step: str, event: str) -> None: ...
    async def on_step_skip(self, step: str) -> None: ...
    async def on_step_complete(
        self,
        step: str,
        event: str,
        summary: dict[str, Any],
        result_msg: str | None,
        duration_s: float,
        call: CallRecord,
    ) -> None: ...
    async def on_step_error(
        self,
        step: str,
        event: str,
        exc: Exception,
        duration_s: float,
        call: CallRecord,
    ) -> None: ...


class BaseStep(ABC):
    name: str = "step"
    event: str = ""
    requires: tuple[str, ...] = ()

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    @abstractmethod
    async def run(self, ctx: WorkflowContext) -> WorkflowContext: ...

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return None


class BaseNode(ABC):
    stage: StageName
    name: str

    def __init__(self, *, stage, name, steps, enabled=True) -> None:
        self.stage = stage
        self.name = name
        self.steps = steps
        self.enabled = enabled

    async def before_run(self, ctx):
        return ctx

    async def after_run(self, ctx):
        return ctx

    async def on_error(self, ctx, exc):
        return None

    def summarize(self, ctx) -> dict[str, Any]:
        return {}

    def validate(self) -> None:
        order = {s.name: i for i, s in enumerate(self.steps)}
        enabled = {s.name for s in self.steps if s.enabled}
        for s in self.steps:
            if not s.enabled:
                continue
            for dep in s.requires:
                if dep not in enabled:
                    raise ConfigError(
                        f"{self.name}: step '{s.name}' requires '{dep}', which is disabled"
                    )
                if order.get(dep, len(order)) > order[s.name]:
                    raise ConfigError(
                        f"{self.name}: step '{s.name}' requires '{dep}', which is ordered after it"
                    )

    async def run(
        self, ctx, *, observer: StepObserver | None = None
    ) -> WorkflowContext:
        if not self.enabled:
            return ctx
        ctx = await self.before_run(ctx)
        try:
            for step in self.steps:
                if not step.enabled:
                    if observer:
                        await observer.on_step_skip(step.name)
                    continue

                event = step.event or step.name
                if observer:
                    await observer.on_step_start(step.name, event)

                token = begin_step()
                started = perf_counter()
                try:
                    ctx = await step.run(ctx)
                except Exception as exc:
                    duration = perf_counter() - started
                    call = end_step(token)
                    if observer:
                        await observer.on_step_error(
                            step.name, event, exc, duration, call
                        )
                    raise
                duration = perf_counter() - started
                call = end_step(token)

                summary: dict[str, Any] = {}
                result_msg: str | None = None
                try:
                    summary = step.summarize(ctx)
                    result_msg = step.log_message(ctx)
                except Exception:
                    logger.opt(exception=True).debug(
                        "summarize failed for step {}", step.name
                    )

                if observer:
                    await observer.on_step_complete(
                        step.name, event, summary, result_msg, duration, call
                    )
        except Exception as exc:
            await self.on_error(ctx, exc)
            raise
        return await self.after_run(ctx)
