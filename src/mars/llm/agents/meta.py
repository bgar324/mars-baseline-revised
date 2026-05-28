from typing import Any

from mars.llm.agents.base import BaseAgent
from mars.llm.prompts.meta import SYSTEM_INSTRUCTION, build_meta_prompt
from mars.models.persona import PersonaAgent as PersonaModel
from mars.models.s2 import Paper


N_PAPERS = 3


def format_cluster(papers: list[Paper], n_papers: int = N_PAPERS) -> str:
    top_papers = sorted(papers, key=lambda p: p.citation_count or 0, reverse=True)[
        :n_papers
    ]
    return "\n".join(
        f"- {p.title}\n  TLDR: {p.tldr or p.abstract or p.title}" for p in top_papers
    )


class PersonaAgent(BaseAgent[PersonaModel]):
    """Synthesizes one paper cluster into a debating persona."""

    name: str = "persona_synthesis"
    role: str = "Synthesizes a citation-grounded paper cluster into a debating persona."
    system_instruction: str = SYSTEM_INSTRUCTION

    def build_input(self, context: dict[str, Any]) -> str:
        return build_meta_prompt(
            focal_claim=context["focal_claim"],
            cluster_summary=format_cluster(context["cluster_papers"]),
        )

    def response_schema(self) -> type[PersonaModel]:
        return PersonaModel

    async def run(self, context: dict[str, Any]) -> PersonaModel:
        prompt = self.build_input(context)
        result = await self._with_retries(lambda: self._generate(prompt))
        persona = result.parsed

        persona.cluster_id = context["cluster_id"]
        persona.references = [
            p.id
            for p in sorted(
                context["cluster_papers"],
                key=lambda p: p.citation_count or 0,
                reverse=True,
            )
        ]
        return persona
