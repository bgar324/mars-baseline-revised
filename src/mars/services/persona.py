import asyncio

from mars.config.settings import GeminiSettings
from mars.llm.prompts.persona import SYSTEM_INSTRUCTION, build_persona_prompt
from mars.llm.providers.gemini import GoogleGeminiClient
from mars.models.s2 import Paper
from mars.schemas.persona import PersonaAgent


TOP_N_PAPERS = 5


def format_cluster(papers: list[Paper], top_n: int = TOP_N_PAPERS) -> str:
    top = sorted(papers, key=lambda p: p.citation_count or 0, reverse=True)[:top_n]
    return "\n".join(
        f"- {p.title}\n  TLDR: {p.tldr or p.abstract or p.title}" for p in top
    )


async def synthesize_persona(
    cluster_id: int,
    cluster_papers: list[Paper],
    focal_claim: str,
    client: GoogleGeminiClient,
    config: GeminiSettings | None = None,
) -> PersonaAgent:
    summary = format_cluster(cluster_papers)
    prompt = build_persona_prompt(focal_claim=focal_claim, cluster_summary=summary)

    persona = await client.generate_structured(
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        schema=PersonaAgent,
        config=config,
    )

    persona.cluster_id = cluster_id
    persona.references = [
        p.id
        for p in sorted(
            cluster_papers,
            key=lambda p: p.citation_count or 0,
            reverse=True,
        )
    ]
    return persona


async def synthesize_personas(
    clusters: dict[int, list[Paper]],
    focal_claim: str,
    client: GoogleGeminiClient,
    config: GeminiSettings | None = None,
    min_cluster_size: int = 5,
) -> list[PersonaAgent]:
    eligible = {
        cid: papers
        for cid, papers in clusters.items()
        if cid != -1 and len(papers) >= min_cluster_size
    }

    tasks = [
        synthesize_persona(cid, papers, focal_claim, client, config)
        for cid, papers in eligible.items()
    ]
    return await asyncio.gather(*tasks)
