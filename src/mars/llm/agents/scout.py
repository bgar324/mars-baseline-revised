from mars.client.s2 import SemanticScholarClient
from mars.llm.prompts.scout import (
    REPHRASE_SYSTEM,
    SYSTEM_PROMPT,
    build_query_prompt,
    build_rephrase_prompt,
)
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import EvidenceSet, EvidenceSnippet, ScoutQueries, SearchQuery
from mars.models.s2 import Snippet
from mars.utils.debate_log import log


PRIMARY_K = 5
SECONDARY_K = 4
JUDGE_K = 6


def _to_snippets(hits: list[Snippet], tier: str) -> list[EvidenceSnippet]:
    out: list[EvidenceSnippet] = []
    for h in hits:
        if h.paper.corpus_id is None:
            continue
        out.append(
            EvidenceSnippet(
                corpus_id=str(h.paper.corpus_id),
                title=h.paper.title,
                section=h.section,
                text=h.text,
                score=h.score,
                tier=tier,
            )
        )
    return out


def _dedup(snippets: list[EvidenceSnippet]) -> list[EvidenceSnippet]:
    seen: set[tuple[str, str | None]] = set()
    keep: list[EvidenceSnippet] = []
    for s in snippets:
        key = (s.corpus_id, s.section)
        if key not in seen:
            seen.add(key)
            keep.append(s)
    return keep


class ScoutAgent:
    def __init__(self, *, s2: SemanticScholarClient, provider: LLMProvider) -> None:
        self._s2 = s2
        self._provider = provider

    async def for_persona(
        self,
        *,
        agent_id: str,
        framing: str,
        focal_claim: str,
        claim: str,
        cluster_paper_ids: list[str],
        secondary_filters: dict | None = None,
    ) -> tuple[EvidenceSet, TokenUsage]:
        queries, usage = await self._queries(framing, focal_claim, claim)

        primary: list[EvidenceSnippet] = []
        for q in queries.primary:
            log("INFO", "scout", "call", "for_persona", f"agent {agent_id} primary: {q!r}")
            hits = await self._s2.search_snippets(q, paper_ids=cluster_paper_ids, limit=PRIMARY_K)
            primary.extend(_to_snippets(hits, "primary"))

        log("INFO", "scout", "call", "for_persona", f"agent {agent_id} secondary: {queries.secondary!r}")
        secondary_hits = await self._s2.search_snippets(
            queries.secondary, limit=SECONDARY_K, **(secondary_filters or {})
        )
        secondary = _to_snippets(secondary_hits, "secondary")

        if not primary:
            log("WARN", "scout", "warn", "for_persona",
                f"agent {agent_id}: no cluster passages for claim — sparse cluster or off-base claim")
        if not secondary:
            log("WARN", "scout", "warn", "for_persona",
                f"agent {agent_id}: open search returned nothing — check rephrased query")

        bundle = EvidenceSet(snippets=_dedup(primary + secondary))
        log(
            "INFO", "scout", "parsed", "for_persona",
            f"agent {agent_id}: {len(primary)} primary + {len(secondary)} secondary "
            f"-> {len(bundle.snippets)} snippets [{usage}]",
        )
        return bundle, usage

    async def for_judge(
        self,
        *,
        agent_id: str,
        agent_claim: str,
        central_conflict: str,
        agent_cited_ids: list[str],
    ) -> tuple[EvidenceSet, TokenUsage]:
        query, usage = await self._rephrase(agent_claim, central_conflict)

        if not agent_cited_ids:
            log("WARN", "scout", "warn", "for_judge",
                f"agent {agent_id}: cited no evidence — cross-examination has nothing to scope to")
            log("INFO", "scout", "parsed", "for_judge",
                f"agent {agent_id}: 0 snippets [{usage}]")
            return EvidenceSet(), usage

        log("INFO", "scout", "call", "for_judge",
            f"agent {agent_id} cross-exam: {query.query!r} over {len(agent_cited_ids)} papers")
        hits = await self._s2.search_snippets(query.query, paper_ids=agent_cited_ids, limit=JUDGE_K)
        bundle = EvidenceSet(snippets=_dedup(_to_snippets(hits, "judge")))
        log("INFO", "scout", "parsed", "for_judge",
            f"agent {agent_id}: {len(bundle.snippets)} snippets [{usage}]")
        return bundle, usage

    async def _queries(self, framing, focal_claim, claim) -> tuple[ScoutQueries, TokenUsage]:
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_query_prompt(framing, focal_claim, claim)},
            ],
            schema=ScoutQueries,
            thinking_level="minimal",
        )
        return result.parsed, result.usage

    async def _rephrase(self, agent_claim, central_conflict) -> tuple[SearchQuery, TokenUsage]:
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": REPHRASE_SYSTEM},
                {"role": "user", "content": build_rephrase_prompt(agent_claim, central_conflict)},
            ],
            schema=SearchQuery,
            thinking_level="minimal",
        )
        return result.parsed, result.usage
