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
from mars.schemas.query import (
    ExtractedQuery,
    HypotheticalQuestions,
    QueryExpansion,
    QuerySpan,
    SemanticRole,
)


class QueryService:
    """Pipeline stage service for semantic role labeling, term expansion, hypothetical questions."""

    def __init__(
        self,
        *,
        langextract: LangExtractProvider,
        gemini: LLMProvider,
    ) -> None:
        self._langextract = langextract
        self._gemini = gemini

    async def extract(self, query: str) -> ExtractedQuery:
        """Semantic role labeling and declarative-claim synthesis."""
        result = await self._langextract.extract(query)
        spans = srl_to_spans(result)
        claim = await self._synthesize_claim(query, spans)
        return ExtractedQuery(raw_text=query, spans=spans, claim=claim)

    async def _synthesize_claim(
        self, query: str, spans: list[QuerySpan]
    ) -> str:
        domain = next(
            (s.text for s in spans if s.role == SemanticRole.DOMAIN), None
        )
        goal = next(
            (s.text for s in spans if s.role == SemanticRole.GOAL), None
        )
        constructs = [s.text for s in spans if s.role == SemanticRole.CONSTRUCT]
        raw_claim = next(
            (s.text for s in spans if s.role == SemanticRole.CLAIM), None
        )
        prompt = build_claim_prompt(
            query=query,
            domain=domain,
            goal=goal,
            constructs=constructs,
            claim=raw_claim,
        )
        response = await self._gemini.generate(
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content.strip()

    async def expand(
        self, extracted: ExtractedQuery
    ) -> tuple[QueryExpansion, HypotheticalQuestions]:
        """Term expansion + hypothetical-question generation."""
        constructs = [
            (s.id, s.text) for s in extracted.spans if s.role == SemanticRole.CONSTRUCT
        ]
        domain = next(
            (s.text for s in extracted.spans if s.role == SemanticRole.DOMAIN), None
        )
        claim = next(
            (s.text for s in extracted.spans if s.role == SemanticRole.CLAIM), None
        )

        expansion = (
            await self._gemini.generate_structured(
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
        ).parsed

        questions = (
            await self._gemini.generate_structured(
                messages=[
                    {"role": "system", "content": QUESTION_SYSTEM},
                    {
                        "role": "user",
                        "content": build_question_prompt(
                            constructs=[text for _, text in constructs],
                            domain=expansion.domain,
                            claim=claim,
                        ),
                    },
                ],
                schema=HypotheticalQuestions,
            )
        ).parsed

        return expansion, questions


ROLE_MAP = {
    "domain": SemanticRole.DOMAIN,
    "goal": SemanticRole.GOAL,
    "construct": SemanticRole.CONSTRUCT,
    "claim": SemanticRole.CLAIM,
}
ID_PREFIX = {"domain": "d", "goal": "g", "construct": "c", "claim": "claim"}


def srl_to_spans(result) -> list[QuerySpan]:
    """Map a langextract AnnotatedDocument into role-labeled QuerySpans."""
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
