import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from mars.llm.agents.meta import PersonaSynthesizer
from mars.llm.prompts.meta import (
    SYSTEM_PROMPT,
    build_generic_meta_block,
    build_meta_cache_block,
)
from mars.llm.providers.base import LLMProvider
from mars.models.persona import Persona, PersonaDraft
from mars.models.s2 import Paper
from mars.schemas.event import StageName
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext, WorkflowError

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600
PERSONA_PSEUDONYMS = (
    "Aster",
    "Lyra",
    "Atlas",
    "Mira",
    "Orion",
    "Vega",
    "Sol",
    "Nova",
)


@dataclass(frozen=True, slots=True)
class PersonaNodeConfig:
    grounded: bool = True
    min_cluster_size: int = 5
    select_panel: bool = True


def eligible_clusters(
    clusters: dict[int, list[Paper]], min_cluster_size: int
) -> dict[int, list[Paper]]:
    return {
        cid: papers
        for cid, papers in clusters.items()
        if cid != -1 and len(papers) >= min_cluster_size
    }


async def synthesize_personas(
    clusters: dict[int, list[Paper]],
    focal_claim: str,
    provider: LLMProvider,
    min_cluster_size: int = 5,
    only_clusters: list[int] | None = None,
) -> list[Persona]:
    if only_clusters:
        chosen = set(only_clusters)
        eligible = {
            cid: papers
            for cid, papers in clusters.items()
            if cid != -1 and cid in chosen
        }
    else:
        eligible = eligible_clusters(clusters, min_cluster_size)
    agent = PersonaSynthesizer(provider=provider)

    cache_name: str | None = None
    if len(eligible) >= 2:
        try:
            cache_name = await provider.create_cache(
                system_instruction=SYSTEM_PROMPT,
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

    return assign_pseudonyms(list(personas))


async def synthesize_generic_personas(
    focal_claim: str,
    n: int,
    provider: LLMProvider,
) -> list[Persona]:
    async def one(index: int) -> Persona:
        result = await provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_generic_meta_block(focal_claim)},
            ],
            schema=PersonaDraft,
        )
        draft: PersonaDraft = result.parsed
        draft.evidence_relation = "ungrounded"
        return Persona(cluster_id=index, name="", references=[], **draft.model_dump())

    personas = await asyncio.gather(*(one(i) for i in range(n)))
    return assign_pseudonyms(list(personas))


def assign_pseudonyms(personas: list[Persona]) -> list[Persona]:
    for index, persona in enumerate(sorted(personas, key=lambda item: item.cluster_id)):
        base = PERSONA_PSEUDONYMS[index % len(PERSONA_PSEUDONYMS)]
        cycle = index // len(PERSONA_PSEUDONYMS)
        persona.name = base if cycle == 0 else f"{base} {cycle + 1}"
    return personas


class SynthesizePersonasStep(BaseStep):
    name = "persona.synthesize_personas"
    event = "personas.created"
    requires = ()

    def __init__(
        self,
        gemini: LLMProvider,
        *,
        grounded: bool = True,
        min_cluster_size: int = 5,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self._gemini = gemini
        self._grounded = grounded
        self._min_cluster_size = min_cluster_size

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        clusters = ctx.clusters or {}
        if self._grounded:
            only_clusters = None if ctx.mode == "manual" else ctx.perspectives
            personas = await synthesize_personas(
                clusters,
                ctx.extracted.claim,
                self._gemini,
                self._min_cluster_size,
                only_clusters=only_clusters,
            )
        else:
            n = len(eligible_clusters(clusters, self._min_cluster_size))
            personas = await synthesize_generic_personas(
                ctx.extracted.claim, n, self._gemini
            )
        if not personas:
            raise WorkflowError(
                "No researcher personas could be formed (too few clustered papers). "
                "Try a broader query."
            )
        ctx.persona_pool = personas
        ctx.personas = personas
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"personas": len(ctx.personas)}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return f"{len(ctx.personas)} personas"


class SelectPanelStep(BaseStep):
    name = "persona.select_panel"
    event = "panel.selected"
    requires = ("persona.synthesize_personas",)

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        pool = ctx.require_persona_pool()
        if ctx.mode != "manual" and ctx.perspectives:
            ids = set(ctx.perspectives)
            ctx.personas = [p for p in pool if p.cluster_id in ids]
        else:
            ctx.personas = list(pool)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"participants": len(ctx.personas)}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        if not ctx.personas:
            return None
        names = ", ".join(persona.name for persona in ctx.personas)
        return f"{len(ctx.personas)} participants: {names}"


class PersonaNode(BaseNode):
    def __init__(
        self,
        *,
        gemini: LLMProvider,
        config: PersonaNodeConfig | None = None,
    ) -> None:
        cfg = config or PersonaNodeConfig()
        super().__init__(
            stage=StageName.PERSONA,
            name="persona",
            steps=[
                SynthesizePersonasStep(
                    gemini,
                    grounded=cfg.grounded,
                    min_cluster_size=cfg.min_cluster_size,
                ),
                SelectPanelStep(enabled=cfg.select_panel),
            ],
        )

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "pool": len(ctx.persona_pool or []),
            "personas": len(ctx.personas),
        }
