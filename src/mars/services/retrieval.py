import asyncio
import logging
from typing import Literal

from mars.client.s2 import SemanticScholarClient
from mars.config.pipeline import RetrievalConfig
from mars.models.s2 import Paper
from mars.schemas.query import (
    ExtractedQuery,
    HypotheticalQuestions,
    QueryExpansion,
    RetrievalAnchors,
    SemanticRole,
)

logger = logging.getLogger(__name__)

AnchorMode = Literal["search", "snippets"]


class RetrievalService:
    """Pipeline stage service for literature retrieval."""

    def __init__(
        self,
        *,
        s2: SemanticScholarClient,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._s2 = s2
        self._config = config or RetrievalConfig()

    async def retrieve(
        self,
        extracted: ExtractedQuery,
        expansion: QueryExpansion,
        questions: HypotheticalQuestions,
    ) -> list[Paper]:
        return await retrieve_literature(
            extracted, expansion, questions, self._s2, self._config
        )


def build_anchors(
    extracted: ExtractedQuery,
    expansion: QueryExpansion,
    questions: HypotheticalQuestions,
) -> RetrievalAnchors:
    construct_queries = [
        f"{ec.construct_text} {' '.join(ec.expansions)}" for ec in expansion.expansions
    ]
    claim_span = next(
        (s for s in extracted.spans if s.role == SemanticRole.CLAIM),
        None,
    )
    return RetrievalAnchors(
        construct_queries=construct_queries,
        hypothetical_queries=list(questions.questions),
        claim_query=claim_span.text if claim_span else None,
    )


async def retrieve_for_anchor(
    client: SemanticScholarClient,
    anchor: str,
    config: RetrievalConfig,
    mode: AnchorMode,
) -> list[Paper]:
    if mode == "search":
        return await client.search(
            anchor,
            limit=config.papers_per_anchor,
            publicationTypes=",".join(pt.value for pt in config.publication_types)
            or None,
            minCitationCount=config.min_citation_count,
        )
    snippets = await client.search_snippets(
        anchor,
        limit=config.snippets_per_anchor,
        minCitationCount=config.min_citation_count,
    )
    return [s.paper for s in snippets]


def deduplicate(papers: list[Paper]) -> list[Paper]:
    seen: dict[str, Paper] = {}
    for paper in papers:
        if not paper.id:
            continue
        existing = seen.get(paper.id)
        if existing is None:
            seen[paper.id] = paper
            continue
        if paper.specter_v2 and not existing.specter_v2:
            seen[paper.id] = paper
        elif paper.abstract and not existing.abstract:
            seen[paper.id] = paper
    return list(seen.values())


async def retrieve_candidates(
    client: SemanticScholarClient,
    anchors: RetrievalAnchors,
    config: RetrievalConfig,
) -> list[Paper]:
    tasks: list = [
        retrieve_for_anchor(client, q, config, mode="search")
        for q in anchors.construct_queries
    ]
    tasks.extend(
        retrieve_for_anchor(client, q, config, mode="snippets")
        for q in anchors.hypothetical_queries
    )
    if anchors.claim_query:
        tasks.append(
            retrieve_for_anchor(client, anchors.claim_query, config, mode="snippets")
        )
    results = await asyncio.gather(*tasks, return_exceptions=True)
    flat: list[Paper] = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("retrieval anchor failed, skipping: %s", result)
            continue
        flat.extend(result)
    snippet_corpus_ids = {
        p.corpus_id for p in flat if not p.id and p.corpus_id is not None
    }
    if snippet_corpus_ids:
        hydrated = await client.batch_papers(
            [f"CorpusId:{cid}" for cid in snippet_corpus_ids]
        )
        flat = [p for p in flat if p.id] + hydrated
    return deduplicate(flat)[: config.retrieval_budget]


async def expand_corpus(
    client: SemanticScholarClient,
    papers: list[Paper],
    config: RetrievalConfig,
) -> list[Paper]:
    """Grow a thin candidate set with recommended neighbors until it hits the target size."""
    corpus = deduplicate(papers)
    if config.expansion_rounds <= 0 or len(corpus) >= config.target_corpus_size:
        return corpus[: config.retrieval_budget]

    seen_ids = {p.id for p in corpus if p.id}
    for _ in range(config.expansion_rounds):
        if len(corpus) >= config.target_corpus_size:
            break
        seeds = [
            p.id
            for p in sorted(corpus, key=lambda p: p.citation_count or 0, reverse=True)
            if p.id
        ][: config.expansion_seed_size]
        if not seeds:
            break
        recommended = await client.recommendations(
            positive_paper_ids=seeds, limit=config.expansion_limit
        )
        fresh = [
            p
            for p in recommended
            if p.id
            and p.id not in seen_ids
            and (p.citation_count or 0) >= config.min_citation_count
        ]
        if not fresh:
            break
        seen_ids.update(p.id for p in fresh)
        corpus = deduplicate(corpus + fresh)

    return corpus[: config.retrieval_budget]


async def retrieve_literature(
    extracted: ExtractedQuery,
    expansion: QueryExpansion,
    questions: HypotheticalQuestions,
    client: SemanticScholarClient,
    config: RetrievalConfig | None = None,
) -> list[Paper]:
    """Retrieve candidate papers from Query Expansion outputs."""
    cfg = config or RetrievalConfig()
    anchors = build_anchors(extracted, expansion, questions)
    candidates = await retrieve_candidates(client, anchors, cfg)
    return await expand_corpus(client, candidates, cfg)
