from mars.llm.agents.persona import render_agents, render_turns
from mars.llm.prompts.judge import JUDGE_SYSTEM_PROMPT, SYNTHESIZE_PROMPT
from mars.llm.providers.base import LLMProvider
from mars.models.debate import Cycle, DebateSynthesis
from mars.models.persona import PersonaAgent as PersonaModel


JUDGE_TEMP = 0.2


class Judge:
    """Synthesizes a completed debate cycle."""

    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def synthesize(
        self,
        *,
        cycle: Cycle,
        agents: list[PersonaModel],
    ) -> DebateSynthesis:
        names = {str(a.cluster_id): a.name for a in agents}
        user = SYNTHESIZE_PROMPT.format(
            focal_claim=cycle.focal_claim,
            agents=render_agents(agents),
            turns=render_turns(cycle.turns, names),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            schema=DebateSynthesis,
            temperature=JUDGE_TEMP,
        )
        synthesis = result.parsed
        synthesis.cycle_id = cycle.cycle_id
        return synthesis
