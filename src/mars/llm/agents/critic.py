from mars.llm.prompts.critic import (
    CLASSIFY_SYSTEM,
    DECOMPOSE_SYSTEM,
    build_classify_prompt,
    build_decompose_prompt,
)
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import (
    ClaimDecomposition,
    Counterclaim,
    CounterVerdict,
    EvidenceSet,
)


def passage_lines(internal: EvidenceSet, external: EvidenceSet) -> str:
    lines: list[str] = []
    for label, evidence in (("internal", internal), ("external", external)):
        for snippet in evidence.snippets:
            lines.append(f"- [corpus_id {snippet.corpus_id}] ({label}) {snippet.text}")
    return "\n".join(lines) or "- none"


class CriticAgent:
    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def decompose(
        self, *, claim: str, central_conflict: str
    ) -> tuple[ClaimDecomposition, TokenUsage]:
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": DECOMPOSE_SYSTEM},
                {
                    "role": "user",
                    "content": build_decompose_prompt(claim, central_conflict),
                },
            ],
            schema=ClaimDecomposition,
            thinking_level="medium",
        )
        return result.parsed, result.usage

    async def classify(
        self,
        *,
        decomposition: ClaimDecomposition,
        internal: EvidenceSet,
        external: EvidenceSet,
    ) -> tuple[Counterclaim, TokenUsage]:
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {
                    "role": "user",
                    "content": build_classify_prompt(
                        decomposition.claim,
                        decomposition.mechanism,
                        decomposition.assumption,
                        decomposition.weakness,
                        passage_lines(internal, external),
                    ),
                },
            ],
            schema=CounterVerdict,
            thinking_level="medium",
        )
        verdict: CounterVerdict = result.parsed
        return Counterclaim(decomposition=decomposition, verdict=verdict), result.usage
