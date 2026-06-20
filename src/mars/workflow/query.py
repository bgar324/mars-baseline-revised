from dataclasses import dataclass
from typing import Any

from mars.llm.prompts.query import (
    SYSTEM_INSTRUCTION as EXPANSION_SYSTEM,
    build_claim_prompt,
    build_expansion_prompt,
)
from mars.llm.prompts.question import (
    SYSTEM_INSTRUCTION as QUESTION_SYSTEM,
    build_question_prompt,
)
from mars.llm.providers.base import LLMProvider
from mars.llm.providers.langextract import LangExtractProvider
from mars.llm.providers.usage import note_model
from mars.schemas.event import StageName
from mars.schemas.query import (
    ExtractedQuery,
    HypotheticalQuestions,
    QueryExpansion,
    QuerySpan,
    SemanticRole,
)
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext

QUESTION_TEMP = 0.4

ROLE_MAP = {
    "domain": SemanticRole.DOMAIN,
    "goal": SemanticRole.GOAL,
    "construct": SemanticRole.CONSTRUCT,
    "claim": SemanticRole.CLAIM,
}
ID_PREFIX = {"domain": "d", "goal": "g", "construct": "c", "claim": "claim"}


def srl_to_spans(result) -> list[QuerySpan]:
    spans: list[QuerySpan] = []
    counters = {role: 0 for role in ROLE_MAP}
    for ext in result.extractions:
        cls = ext.extraction_class
        if cls not in ROLE_MAP:
            continue
        idx = counters[cls]
        counters[cls] += 1
        span = ext.char_interval
        spans.append(
            QuerySpan(
                id=f"{ID_PREFIX[cls]}{idx}",
                text=ext.extraction_text,
                char_span=(
                    span.start_pos if span else 0,
                    span.end_pos if span else 0,
                ),
                role=ROLE_MAP[cls],
            )
        )
    return spans


@dataclass(frozen=True, slots=True)
class QueryNodeConfig: ...


class ExtractSpansStep(BaseStep):
    name = "query.extract_spans"
    event = "query.decomposed"
    requires = ()

    def __init__(
        self, langextract: LangExtractProvider, *, enabled: bool = True
    ) -> None:
        super().__init__(enabled=enabled)
        self._langextract = langextract

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        result = await self._langextract.extract(ctx.raw_text)
        spans = srl_to_spans(result)
        ctx.extracted = ExtractedQuery(raw_text=ctx.raw_text, spans=spans, claim="")
        note_model("langextract", self._langextract._settings.model_id)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"spans": len(ctx.extracted.spans) if ctx.extracted else 0}


class SynthesizeClaimStep(BaseStep):
    name = "query.synthesize_claim"
    event = "query.claim_refined"
    requires = ("query.extract_spans",)

    def __init__(self, gemini: LLMProvider, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self._gemini = gemini

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        spans = ctx.extracted.spans
        domain = next((s.text for s in spans if s.role == SemanticRole.DOMAIN), None)
        goal = next((s.text for s in spans if s.role == SemanticRole.GOAL), None)
        constructs = [s.text for s in spans if s.role == SemanticRole.CONSTRUCT]
        raw_claim = next((s.text for s in spans if s.role == SemanticRole.CLAIM), None)
        prompt = build_claim_prompt(
            query=ctx.raw_text,
            domain=domain,
            goal=goal,
            constructs=constructs,
            claim=raw_claim,
        )
        response = await self._gemini.generate(
            messages=[{"role": "user", "content": prompt}],
            thinking_level="minimal",
        )
        ctx.extracted = ctx.extracted.model_copy(
            update={"claim": response.content.strip()}
        )
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"claim": ctx.extracted.claim}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return f"claim: {ctx.extracted.claim}"


class ExpandQueryStep(BaseStep):
    name = "query.expand_query"
    event = "query.expanded"
    requires = ("query.extract_spans",)

    def __init__(self, gemini: LLMProvider, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self._gemini = gemini

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        spans = ctx.extracted.spans
        constructs = [(s.id, s.text) for s in spans if s.role == SemanticRole.CONSTRUCT]
        domain = next((s.text for s in spans if s.role == SemanticRole.DOMAIN), None)
        result = await self._gemini.generate_structured(
            messages=[
                {"role": "system", "content": EXPANSION_SYSTEM},
                {
                    "role": "user",
                    "content": build_expansion_prompt(
                        constructs=constructs, domain=domain
                    ),
                },
            ],
            schema=QueryExpansion,
        )
        ctx.expansion = result.parsed
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "domain": ctx.expansion.domain,
            "constructs": len(ctx.expansion.expansions),
        }

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return f"{len(ctx.expansion.expansions)} constructs"


class GenerateQuestionsStep(BaseStep):
    name = "query.generate_questions"
    event = "query.questions_generated"
    requires = ("query.expand_query",)

    def __init__(self, gemini: LLMProvider, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self._gemini = gemini

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        spans = ctx.extracted.spans
        constructs = [s.text for s in spans if s.role == SemanticRole.CONSTRUCT]
        claim = next((s.text for s in spans if s.role == SemanticRole.CLAIM), None)
        result = await self._gemini.generate_structured(
            messages=[
                {"role": "system", "content": QUESTION_SYSTEM},
                {
                    "role": "user",
                    "content": build_question_prompt(
                        constructs=constructs,
                        domain=ctx.expansion.domain,
                        claim=claim,
                    ),
                },
            ],
            schema=HypotheticalQuestions,
            temperature=QUESTION_TEMP,
        )
        ctx.questions = result.parsed
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"questions": len(ctx.questions.questions)}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return f"{len(ctx.questions.questions)} questions"


class QueryNode(BaseNode):
    def __init__(
        self,
        *,
        langextract: LangExtractProvider,
        gemini: LLMProvider,
        config: QueryNodeConfig | None = None,
    ) -> None:
        steps = [
            ExtractSpansStep(langextract),
            SynthesizeClaimStep(gemini),
            ExpandQueryStep(gemini),
            GenerateQuestionsStep(gemini),
        ]
        super().__init__(stage=StageName.EXTRACT, name="query", steps=steps)

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "claim": ctx.extracted.claim if ctx.extracted else None,
            "constructs": len(ctx.expansion.expansions) if ctx.expansion else 0,
            "questions": len(ctx.questions.questions) if ctx.questions else 0,
        }
