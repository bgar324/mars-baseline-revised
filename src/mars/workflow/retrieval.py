import asyncio
import logging
from typing import Any

from loguru import logger as loguru_logger

from mars.client.s2 import SemanticScholarClient
from mars.config.pipeline import RetrievalConfig
from mars.models.s2 import Paper
from mars.schemas.event import StageName
from mars.schemas.query import (
    ExtractedQuery,
    HypotheticalQuestions,
    RetrievalAnchors,
    SemanticRole,
)
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext

logger = logging.getLogger(__name__)
_diag = loguru_logger.bind(source="workflow.retrieve", stage="retrieve")

QUESTION_ANCHORS = 5


def _paper_key(paper: Paper) -> str | None:
    if paper.id:
        return paper.id
    if paper.corpus_id is not None:
        return f"corpus:{paper.corpus_id}"
    return None


def _paper_ref(paper: Paper) -> str | None:
    if paper.id:
        return paper.id
    if paper.corpus_id is not None:
        return f"CorpusId:{paper.corpus_id}"
    return None


def build_anchors(
    extracted: ExtractedQuery,
    questions: HypotheticalQuestions,
) -> RetrievalAnchors:
    claim_span = next(
        (s for s in extracted.spans if s.role == SemanticRole.CLAIM),
        None,
    )
    return RetrievalAnchors(
        hypothetical_queries=list(questions.questions)[:QUESTION_ANCHORS],
        claim_query=claim_span.text if claim_span else None,
    )


async def retrieve_snippets(
    client: SemanticScholarClient,
    anchor: str,
    config: RetrievalConfig,
) -> list[Paper]:
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
) -> tuple[list[Paper], list[dict[str, Any]]]:
    queries: list[str] = list(anchors.hypothetical_queries)
    if anchors.claim_query:
        queries.append(anchors.claim_query)

    results = await asyncio.gather(
        *(retrieve_snippets(client, q, config) for q in queries),
        return_exceptions=True,
    )

    flat: list[Paper] = []
    seen: set[str] = set()
    per_query: list[dict[str, Any]] = []
    for query, result in zip(queries, results):
        if isinstance(result, Exception):
            logger.warning("retrieval anchor failed, skipping: %s", result)
            per_query.append(
                {
                    "query": query,
                    "mode": "snippets",
                    "papers": 0,
                    "new": 0,
                    "duplicate": 0,
                }
            )
            continue
        keys = {k for p in result if (k := _paper_key(p))}
        new = len(keys - seen)
        seen |= keys
        per_query.append(
            {
                "query": query,
                "mode": "snippets",
                "papers": len(result),
                "new": new,
                "duplicate": len(result) - new,
            }
        )
        _diag.info(
            "query | snippets | {} papers ({} new, {} dup) | {!r}",
            len(result),
            new,
            len(result) - new,
            query[:80],
        )
        flat.extend(result)

    refs: list[str] = []
    seen_refs: set[str] = set()
    for paper in flat:
        ref = _paper_ref(paper)
        if ref and ref not in seen_refs:
            seen_refs.add(ref)
            refs.append(ref)

    hydrated = await client.batch_papers(refs) if refs else []
    deduped = deduplicate(hydrated)
    _diag.info(
        "candidates | {} queries | {} fetched, {} unique, {} hydrated",
        len(queries),
        len(flat),
        len(refs),
        len(deduped),
    )
    return deduped[: config.retrieval_budget], per_query


async def expand_corpus(
    client: SemanticScholarClient,
    papers: list[Paper],
    config: RetrievalConfig,
) -> list[Paper]:
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
        _diag.info("expand round | +{} fresh | {} total", len(fresh), len(corpus))

    return corpus[: config.retrieval_budget]


class BuildAnchorsStep(BaseStep):
    name = "retrieval.build_anchors"
    event = "retrieval.anchors_built"
    requires = ()

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        ctx.anchors = build_anchors(ctx.extracted, ctx.questions)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"snippets": len(ctx.anchors.hypothetical_queries)}


class RetrieveCandidatesStep(BaseStep):
    name = "retrieval.retrieve_candidates"
    event = "retrieval.candidates_retrieved"
    requires = ("retrieval.build_anchors",)

    def __init__(
        self,
        s2: SemanticScholarClient,
        config: RetrievalConfig,
        *,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self._s2 = s2
        self._config = config

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        ctx.papers, ctx.retrieval_diagnostics = await retrieve_candidates(
            self._s2, ctx.anchors, self._config
        )
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        rows = ctx.retrieval_diagnostics or []
        fetched = sum(r["papers"] for r in rows)
        unique = sum(r["new"] for r in rows)
        return {
            "candidates": len(ctx.papers),
            "fetched": fetched,
            "duplicates": fetched - unique,
        }


class ExpandCorpusStep(BaseStep):
    name = "retrieval.expand_corpus"
    event = "papers.retrieved"
    requires = ("retrieval.retrieve_candidates",)

    def __init__(
        self,
        s2: SemanticScholarClient,
        config: RetrievalConfig,
        *,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self._s2 = s2
        self._config = config

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        ctx.papers = await expand_corpus(self._s2, ctx.papers, self._config)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"papers": len(ctx.papers)}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return f"{len(ctx.papers)} papers"


class RetrievalNode(BaseNode):
    def __init__(
        self,
        *,
        s2: SemanticScholarClient,
        config: RetrievalConfig | None = None,
    ) -> None:
        cfg = config or RetrievalConfig()
        steps = [
            BuildAnchorsStep(),
            RetrieveCandidatesStep(s2, cfg),
            ExpandCorpusStep(s2, cfg),
        ]
        super().__init__(stage=StageName.RETRIEVE, name="retrieval", steps=steps)

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"papers": len(ctx.papers)}
