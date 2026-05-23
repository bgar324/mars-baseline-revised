import asyncio

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
        f"{ec.construct} {' '.join(ec.expansions)}" for ec in expansion.expansions
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
    client: SemanticScholarClient, anchor: str, config: RetrievalConfig
) -> list[Paper]:
    papers_task = client.search(
        anchor,
        limit=config.papers_per_anchor,
        publicationTypes=",".join(pt.value for pt in config.publication_types) or None,
        minCitationCount=config.min_citation_count,
    )
    snippets_task = client.search_snippets(
        anchor,
        limit=config.snippets_per_anchor,
        minCitationCount=config.min_citation_count,
    )
    papers, snippets = await asyncio.gather(papers_task, snippets_task)
    return papers + [s.paper for s in snippets]


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
    queries = [*anchors.construct_queries, *anchors.hypothetical_queries]
    if anchors.claim_query:
        queries.append(anchors.claim_query)
    results = await asyncio.gather(
        *(retrieve_for_anchor(client, q, config) for q in queries)
    )
    flat = [p for sub in results for p in sub]
    snippet_corpus_ids = {
        p.corpus_id for p in flat if not p.id and p.corpus_id is not None
    }
    if snippet_corpus_ids:
        hydrated = await client.batch_papers(
            [f"CorpusId:{cid}" for cid in snippet_corpus_ids]
        )
        flat = [p for p in flat if p.id] + hydrated
    return deduplicate(flat)[: config.retrieval_budget]


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
    return await retrieve_candidates(client, anchors, cfg)
