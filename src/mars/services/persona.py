import asyncio

from mars.llm.agents.persona import PersonaAgent
from mars.llm.providers.base import LLMProvider
from mars.models.s2 import Paper
from mars.schemas.persona import PersonaAgent as PersonaSchema


async def synthesize_personas(
    clusters: dict[int, list[Paper]],
    focal_claim: str,
    provider: LLMProvider,
    min_cluster_size: int = 5,
) -> list[PersonaSchema]:
    eligible = {
        cid: papers
        for cid, papers in clusters.items()
        if cid != -1 and len(papers) >= min_cluster_size
    }

    agent = PersonaAgent(provider=provider)
    return await asyncio.gather(
        *(
            agent.run(
                {
                    "cluster_id": cid,
                    "cluster_papers": papers,
                    "focal_claim": focal_claim,
                }
            )
            for cid, papers in eligible.items()
        )
    )
