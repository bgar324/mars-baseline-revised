from collections import Counter
from collections.abc import Iterable
from typing import Any

import numpy as np

from mars.llm.agents.base import BaseAgent
from mars.llm.prompts.meta import (
    SYSTEM_PROMPT,
    build_meta_cluster_block,
    build_meta_prompt,
)
from mars.models.persona import Persona, PersonaDraft
from mars.models.s2 import Paper


TOP_K_CITATIONS = 5
TOP_K_CENTRALITY = 5


def top_k(scores: np.ndarray, k: int) -> list[int]:
    return np.argsort(scores)[::-1][:k].tolist()


def combine_corpus(
    papers: list[Paper],
    top_cited: int = TOP_K_CITATIONS,
    top_central: int = TOP_K_CENTRALITY,
) -> list[Paper]:
    embedded = [p for p in papers if p.specter_v2 is not None]
    if not embedded:
        citations = np.array([p.citation_count or 0 for p in papers], dtype=np.float32)
        return [papers[i] for i in top_k(citations, top_cited)]

    X = np.array([p.specter_v2 for p in embedded], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True).clip(min=1.0)
    centroid = X.mean(axis=0)
    centroid /= np.linalg.norm(centroid) or 1.0
    centrality = X @ centroid

    cited = np.array([p.citation_count or 0 for p in embedded], dtype=np.float32)
    order = dict.fromkeys(top_k(cited, top_cited) + top_k(centrality, top_central))
    return [embedded[i] for i in order]


def top_categories(groups: Iterable[list[str] | None], limit: int = 5) -> str:
    counts = Counter(value for group in groups for value in (group or []))
    return ", ".join(name for name, _ in counts.most_common(limit)) or "n/a"


def year_range(papers: list[Paper]) -> str:
    years = [p.year for p in papers if p.year]
    return f"{min(years)}-{max(years)}" if years else "n/a"


def cluster_summary(papers: list[Paper]) -> str:
    sample = combine_corpus(papers)
    context = (
        "CLUSTER CONTEXT:\n"
        f"cluster size: {len(papers)} papers (the sample below is representative, not exhaustive)\n"
        f"dominant fields of study: {top_categories(p.fields_of_study for p in papers)}\n"
        f"publication types: {top_categories(p.publication_types for p in papers)}\n"
        f"year range: {year_range(papers)}"
    )
    sample_lines = "\n".join(
        f"- {p.title}\n  TLDR: {p.tldr or p.abstract or p.title}" for p in sample
    )
    return f"{context}\n\nSAMPLE PAPERS:\n{sample_lines}"


class PersonaSynthesizer(BaseAgent[PersonaDraft]):
    name: str = "persona_synthesis"
    role: str = "Synthesizes a citation-grounded paper cluster into a debating persona."
    system_instruction: str = SYSTEM_PROMPT

    def build_input(self, context: dict[str, Any]) -> str:
        return build_meta_prompt(
            focal_claim=context["focal_claim"],
            cluster_summary=cluster_summary(context["cluster_papers"]),
        )

    def response_schema(self) -> type[PersonaDraft]:
        return PersonaDraft

    async def run(self, context: dict[str, Any]) -> Persona:
        cache_name = context.get("cache_name")
        prompt = (
            build_meta_cluster_block(cluster_summary(context["cluster_papers"]))
            if cache_name
            else self.build_input(context)
        )
        result = await self._with_retries(
            lambda: self._generate(prompt, cache_name=cache_name)
        )
        draft: PersonaDraft = result.parsed

        references = [
            p.id
            for p in sorted(
                context["cluster_papers"],
                key=lambda p: p.citation_count or 0,
                reverse=True,
            )
        ]
        return Persona(
            cluster_id=context["cluster_id"],
            references=references,
            **draft.model_dump(),
        )
