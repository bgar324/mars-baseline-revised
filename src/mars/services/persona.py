import asyncio
import logging

from mars.llm.agents.meta import PersonaAgent
from mars.llm.prompts.meta import SYSTEM_INSTRUCTION, build_meta_cache_block
from mars.llm.providers.base import LLMProvider
from mars.models.persona import PersonaAgent as PersonaModel
from mars.models.s2 import Paper

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600


class PersonaService:
    def __init__(self, *, gemini: LLMProvider) -> None:
        self._gemini = gemini

    async def synthesize(
        self,
        clusters: dict[int, list[Paper]],
        focal_claim: str,
        min_cluster_size: int = 5,
    ) -> list[PersonaModel]:
        return await synthesize_personas(
            clusters, focal_claim, self._gemini, min_cluster_size
        )


async def synthesize_personas(
    clusters: dict[int, list[Paper]],
    focal_claim: str,
    provider: LLMProvider,
    min_cluster_size: int = 5,
) -> list[PersonaModel]:
    eligible = {
        cid: papers
        for cid, papers in clusters.items()
        if cid != -1 and len(papers) >= min_cluster_size
    }

    agent = PersonaAgent(provider=provider)

    cache_name: str | None = None
    if len(eligible) >= 2:
        try:
            cache_name = await provider.create_cache(
                system_instruction=SYSTEM_INSTRUCTION,
                content=build_meta_cache_block(focal_claim),
                ttl_seconds=CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("persona cache creation failed, running uncached: %s", exc)
            cache_name = None

    try:
        personas = await asyncio.gather(
            *(
                agent.run(
                    {
                        "cluster_id": cid,
                        "cluster_papers": papers,
                        "focal_claim": focal_claim,
                        "cache_name": cache_name,
                    }
                )
                for cid, papers in eligible.items()
            )
        )
    finally:
        if cache_name:
            await provider.delete_cache(cache_name)

    return ensure_distinct_names(list(personas))


def ensure_distinct_names(personas: list[PersonaModel]) -> list[PersonaModel]:
    seen: set[str] = set()
    for persona in personas:
        key = persona.name.strip().lower()
        if key not in seen:
            seen.add(key)
            continue
        ordinal = 2
        while f"{persona.name} ({ordinal})".lower() in seen:
            ordinal += 1
        persona.name = f"{persona.name} ({ordinal})"
        seen.add(persona.name.lower())
    return personas
