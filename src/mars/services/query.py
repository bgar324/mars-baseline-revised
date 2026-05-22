from mars.llm.prompts.query import (
    SYSTEM_INSTRUCTION as EXPANSION_SYSTEM,
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
        """Semantic role labeling of the raw query."""
        result = await self._langextract.extract(query)
        return srl_to_extracted_query(query, result)

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


def srl_to_extracted_query(raw_text: str, result) -> ExtractedQuery:
    """Map a langextract AnnotatedDocument into an ExtractedQuery."""
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
    return ExtractedQuery(raw_text=raw_text, spans=spans)
