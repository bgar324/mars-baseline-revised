from collections import Counter
from typing import Any

import numpy as np

from mars.llm.agents.base import BaseAgent
from mars.llm.prompts.meta import (
    SYSTEM_INSTRUCTION,
    build_meta_cluster_block,
    build_meta_prompt,
)
from mars.models.persona import PersonaAgent as PersonaModel
from mars.models.persona import PersonaSynthesis
from mars.models.s2 import Paper


K_CITED = 5
K_CENTRAL = 5


def blend_papers(
    papers: list[Paper], k_cited: int = K_CITED, k_central: int = K_CENTRAL
) -> list[Paper]:
    embedded = [p for p in papers if p.specter_v2 is not None]
    if not embedded:
        return sorted(papers, key=lambda p: p.citation_count or 0, reverse=True)[
            :k_cited
        ]

    matrix = np.array([p.specter_v2 for p in embedded], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    centroid = matrix.mean(axis=0)
    centroid /= np.linalg.norm(centroid) or 1.0
    centrality = matrix @ centroid

    by_cited = sorted(
        range(len(embedded)),
        key=lambda i: embedded[i].citation_count or 0,
        reverse=True,
    )[:k_cited]
    by_central = sorted(
        range(len(embedded)), key=lambda i: float(centrality[i]), reverse=True
    )[:k_central]
    order = list(dict.fromkeys([*by_cited, *by_central]))
    return [embedded[i] for i in order]


def format_cluster(papers: list[Paper]) -> str:
    selected = blend_papers(papers)
    fields = Counter(f for p in papers for f in (p.fields_of_study or []))
    ptypes = Counter(t for p in papers for t in (p.publication_types or []))
    years = [p.year for p in papers if p.year]
    year_range = f"{min(years)}-{max(years)}" if years else "n/a"

    context = (
        f"CLUSTER CONTEXT:\n"
        f"cluster size: {len(papers)} papers (the sample below is representative, not exhaustive)\n"
        f"dominant fields of study: {', '.join(f for f, _ in fields.most_common(5)) or 'n/a'}\n"
        f"publication types: {', '.join(t for t, _ in ptypes.most_common(5)) or 'n/a'}\n"
        f"year range: {year_range}"
    )
    sample = "SAMPLE PAPERS:\n" + "\n".join(
        f"- {p.title}\n  TLDR: {p.tldr or p.abstract or p.title}" for p in selected
    )
    return f"{context}\n\n{sample}"


class PersonaAgent(BaseAgent[PersonaSynthesis]):
    name: str = "persona_synthesis"
    role: str = "Synthesizes a citation-grounded paper cluster into a debating persona."
    system_instruction: str = SYSTEM_INSTRUCTION

    def build_input(self, context: dict[str, Any]) -> str:
        return build_meta_prompt(
            focal_claim=context["focal_claim"],
            cluster_summary=format_cluster(context["cluster_papers"]),
        )

    def response_schema(self) -> type[PersonaSynthesis]:
        return PersonaSynthesis

    async def run(self, context: dict[str, Any]) -> PersonaModel:
        cache_name = context.get("cache_name")
        if cache_name:
            prompt = build_meta_cluster_block(format_cluster(context["cluster_papers"]))
        else:
            prompt = self.build_input(context)
        result = await self._with_retries(
            lambda: self._generate(prompt, cache_name=cache_name)
        )
        draft: PersonaSynthesis = result.parsed

        references = [
            p.id
            for p in sorted(
                context["cluster_papers"],
                key=lambda p: p.citation_count or 0,
                reverse=True,
            )
        ]
        return PersonaModel(
            cluster_id=context["cluster_id"],
            name=draft.name,
            framing=draft.framing,
            background=draft.background,
            methods_summary=draft.methods_summary,
            reasoning_style=draft.reasoning_style,
            evaluation_lens=draft.evaluation_lens,
            references=references,
            instructions=draft.instructions,
        )
