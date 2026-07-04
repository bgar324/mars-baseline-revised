from loguru import logger

from mars.client.s2 import SemanticScholarClient
from mars.llm.prompts.scout import (
    SYSTEM_PROMPT,
    build_query_prompt,
    build_rephrase_prompt,
)
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import EvidenceSet, EvidenceSnippet, ScoutQueries, SearchQuery
from mars.models.s2 import Snippet

slog = logger.bind(source="llm.scout", stage="scout")

PRIMARY_K = 5
SECONDARY_K = 4
JUDGE_K = 6
RELATION_K = 6
COUNTER_RECS = 20
COUNTER_K = 5


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


def _dedup_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    keep: list[str] = []
    for i in ids:
        if i and i not in seen:
            seen.add(i)
            keep.append(i)
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
            slog.debug("for_persona | agent {} primary: {!r}", agent_id, q)
            hits = await self._s2.search_snippets(
                q, paper_ids=cluster_paper_ids, limit=PRIMARY_K
            )
            primary.extend(_to_snippets(hits, "primary"))

        slog.debug(
            "for_persona | agent {} secondary: {!r}", agent_id, queries.secondary
        )
        secondary_hits = await self._s2.search_snippets(
            queries.secondary, limit=SECONDARY_K, **(secondary_filters or {})
        )
        secondary = _to_snippets(secondary_hits, "secondary")

        if not primary:
            slog.warning(
                "for_persona | agent {}: no cluster passages for claim — sparse cluster or off-base claim",
                agent_id,
            )
        if not secondary:
            slog.warning(
                "for_persona | agent {}: open search returned nothing — check rephrased query",
                agent_id,
            )

        bundle = EvidenceSet(snippets=_dedup(primary + secondary))
        fetched = len(primary) + len(secondary)
        slog.info(
            "for_persona | agent {} | {} primary + {} secondary fetched, {} unique, {} duplicate",
            agent_id,
            len(primary),
            len(secondary),
            len(bundle.snippets),
            fetched - len(bundle.snippets),
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
            slog.warning(
                "for_judge | agent {}: cited no evidence — cross-examination has nothing to scope to",
                agent_id,
            )
            return EvidenceSet(), usage

        slog.debug(
            "for_judge | agent {} cross-exam: {!r} over {} papers",
            agent_id,
            query.query,
            len(agent_cited_ids),
        )
        hits = await self._s2.search_snippets(
            query.query, paper_ids=agent_cited_ids, limit=JUDGE_K
        )
        snippets = _to_snippets(hits, "judge")
        bundle = EvidenceSet(snippets=_dedup(snippets))
        slog.info(
            "for_judge | agent {} over {} papers | {} fetched, {} unique, {} duplicate",
            agent_id,
            len(agent_cited_ids),
            len(snippets),
            len(bundle.snippets),
            len(snippets) - len(bundle.snippets),
        )
        return bundle, usage

    async def for_relation(
        self,
        *,
        relation_claim: str,
        central_conflict: str,
        mechanism_ids: list[str],
    ) -> tuple[EvidenceSet, TokenUsage]:
        query, usage = await self._rephrase(relation_claim, central_conflict)

        ids = _dedup_ids(mechanism_ids)
        if len(ids) < 2:
            slog.warning(
                "for_relation: relation joins fewer than two distinct mechanisms "
                "({} cited ids) - nothing to test an interaction over",
                len(ids),
            )
            return EvidenceSet(), usage

        slog.debug("for_relation | query {!r} over {} papers", query.query, len(ids))
        hits = await self._s2.search_snippets(
            query.query, paper_ids=ids, limit=RELATION_K
        )
        snippets = _to_snippets(hits, "relation")
        bundle = EvidenceSet(snippets=_dedup(snippets))
        if not bundle.snippets:
            slog.warning(
                "for_relation: no passage in the cited set bears on the claim "
                "- relation likely ungrounded; hypothesis should stay predictive",
            )
        slog.info(
            "for_relation over {} papers | {} fetched, {} unique, {} duplicate",
            len(ids),
            len(snippets),
            len(bundle.snippets),
            len(snippets) - len(bundle.snippets),
        )
        return bundle, usage

    async def for_counter(
        self,
        *,
        counter_queries: list[str],
        internal_seed_ids: list[str],
        external_seed_ids: list[str],
    ) -> tuple[EvidenceSet, EvidenceSet]:
        internal = await self._neighborhood(
            counter_queries, internal_seed_ids, "counter_internal"
        )
        external = await self._neighborhood(
            counter_queries, external_seed_ids, "counter_external"
        )
        slog.info(
            "for_counter | {} internal + {} external snippets",
            len(internal.snippets),
            len(external.snippets),
        )
        return internal, external

    async def _neighborhood(
        self, queries: list[str], seed_ids: list[str], tier: str
    ) -> EvidenceSet:
        ids = _dedup_ids(seed_ids)
        if not ids:
            return EvidenceSet()
        recs = await self._s2.recommendations(
            positive_paper_ids=ids, limit=COUNTER_RECS
        )
        rec_ids = [p.id for p in recs if p.id]
        if not rec_ids:
            return EvidenceSet()
        hits: list[EvidenceSnippet] = []
        for q in queries:
            snips = await self._s2.search_snippets(
                q, paper_ids=rec_ids[:100], limit=COUNTER_K
            )
            hits.extend(_to_snippets(snips, tier))
        return EvidenceSet(snippets=_dedup(hits))

    async def _queries(
        self, framing, focal_claim, claim
    ) -> tuple[ScoutQueries, TokenUsage]:
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_query_prompt(framing, focal_claim, claim),
                },
            ],
            schema=ScoutQueries,
            thinking_level="minimal",
        )
        return result.parsed, result.usage

    async def _rephrase(
        self, agent_claim, central_conflict
    ) -> tuple[SearchQuery, TokenUsage]:
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_rephrase_prompt(agent_claim, central_conflict),
                },
            ],
            schema=SearchQuery,
            thinking_level="minimal",
        )
        return result.parsed, result.usage
