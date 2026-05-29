from mars.llm.prompts.persona import (
    ACTION_PROMPT,
    DEBATE_CONTEXT,
    REFLECT_PROMPT,
    STEERING_BLOCK,
    SYSTEM_PROMPT,
    TURN_PROMPT,
    format_constraints,
    format_list,
)
from mars.llm.providers.base import LLMProvider
from mars.models.debate import (
    AgentTurn,
    AgentTurnInput,
    Cycle,
    Stance,
    Steer,
    TurnType,
)
from mars.models.persona import PersonaAgent as PersonaModel
from mars.models.s2 import Paper


TEMP_BY_TURN: dict[TurnType, float] = {
    "propose": 0.5,
    "respond": 0.4,
    "refine": 0.3,
}
REFLECT_TEMP = 0.2


def render_agents(others: list[PersonaModel]) -> str:
    if not others:
        return "No other agents."
    return "\n".join(f"- {a.name}: {a.framing}" for a in others)


def render_turns(turns: list[AgentTurn], names: dict[str, str] | None = None) -> str:
    if not turns:
        return "No prior turns."
    names = names or {}
    rendered = []
    for t in turns:
        who = names.get(t.agent_id, t.agent_id)
        header = f"[turn_id: {t.turn_id} | {who} | type: {t.turn_type}"
        if t.response_action:
            header += f" | action: {t.response_action}"
        if t.target_turn_id:
            header += f" | target: {t.target_turn_id}"
        header += "]"
        rendered.append(
            f"{header}\nClaim: {t.claim}\nRationale: {t.rationale}\nMessage: {t.message}"
        )
    return "\n\n".join(rendered)


def render_evidence(papers: list[Paper]) -> str:
    if not papers:
        return "No evidence available."
    blocks = []
    for p in papers:
        summary = p.tldr or p.abstract or "No summary available."
        blocks.append(
            f'- "{p.title}" ({p.year or "n.d."})  [paper_id: {p.id}]\n  {summary}'
        )
    return "\n\n".join(blocks)


def build_system_prompt(persona: PersonaModel) -> str:
    return SYSTEM_PROMPT.format(
        name=persona.name,
        framing=persona.framing,
        background=persona.background,
        reasoning_style=persona.reasoning_style,
        evaluation_lens=persona.evaluation_lens,
        instructions=format_list(persona.instructions),
        constraints=format_constraints(persona.constraints),
    )


def build_debate_context(
    cycle: Cycle,
    others: list[PersonaModel],
    evidence: list[Paper],
    recap: str | None,
) -> str:
    return DEBATE_CONTEXT.format(
        focal_claim=cycle.focal_claim,
        recap=recap or "Root cycle — no prior recap.",
        agents=render_agents(others),
        evidence=render_evidence(evidence),
    )


def build_turn_prompt(
    turns: list[AgentTurn], turn_type: TurnType, names: dict[str, str]
) -> str:
    return TURN_PROMPT.format(turns=render_turns(turns, names), turn_type=turn_type)


def build_steering_block(steers: list[Steer] | None, agent_id: str) -> str:
    if not steers:
        return ""
    own = [s for s in steers if s.agent_id == agent_id]
    if not own:
        return ""
    return STEERING_BLOCK.format(
        emphasize=format_list([s.text for s in own if s.type == "emphasize"]),
        reframe=format_list([s.text for s in own if s.type == "reframe"]),
    )


def build_reflect_prompt(
    persona: PersonaModel,
    cycle: Cycle,
    own_turns: list[AgentTurn],
    prior_stance: Stance | None,
) -> str:
    stance = prior_stance or Stance(summary="No prior stance.", cycle_id=cycle.cycle_id)
    return REFLECT_PROMPT.format(
        name=persona.name,
        focal_claim=cycle.focal_claim,
        turns=render_turns(own_turns, {str(persona.cluster_id): persona.name}),
        points_of_agreement=format_list(cycle.synthesis.points_of_agreement),
        points_of_disagreement=format_list(cycle.synthesis.points_of_disagreement),
        questions=format_list(cycle.synthesis.questions),
        stance_summary=stance.summary,
        stance_claims=format_list(stance.claims),
        stance_premises=format_list(stance.premises),
        stance_conflicts=format_list(stance.conflicts),
    )


class PersonaTurnAgent:
    """Speaks for one persona: its debate turns and stance updates."""

    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def produce(
        self,
        *,
        persona: PersonaModel,
        cycle: Cycle,
        others: list[PersonaModel],
        prior_turns: list[AgentTurn],
        turn_type: TurnType,
        evidence: list[Paper],
        recap: str | None = None,
        cache_name: str | None = None,
        steers: list[Steer] | None = None,
    ) -> AgentTurn:
        names = {str(p.cluster_id): p.name for p in (persona, *others)}
        user = build_turn_prompt(prior_turns, turn_type, names)
        if turn_type == "respond":
            user += "\n\n" + ACTION_PROMPT

        steering = build_steering_block(steers, str(persona.cluster_id))
        if steering:
            user = steering + "\n\n" + user

        if cache_name:
            messages = [{"role": "user", "content": user}]
        else:
            system = build_system_prompt(persona)
            context = build_debate_context(cycle, others, evidence, recap)
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": context + "\n\n" + user},
            ]

        result = await self._provider.generate_structured(
            messages=messages,
            schema=AgentTurnInput,
            cache_name=cache_name,
            temperature=TEMP_BY_TURN[turn_type],
        )
        draft = result.parsed
        return AgentTurn(
            cycle_id=cycle.cycle_id,
            agent_id=str(persona.cluster_id),
            turn_type=turn_type,
            response_action=draft.response_action,
            target_turn_id=draft.target_turn_id,
            claim=draft.claim,
            rationale=draft.rationale,
            evidence=draft.evidence,
            message=draft.message,
        )

    async def reflect(
        self,
        *,
        persona: PersonaModel,
        cycle: Cycle,
        own_turns: list[AgentTurn],
        prior_stance: Stance | None,
        cache_name: str | None = None,
    ) -> Stance:
        user = build_reflect_prompt(persona, cycle, own_turns, prior_stance)

        if cache_name:
            messages = [{"role": "user", "content": user}]
        else:
            system = build_system_prompt(persona)
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]

        result = await self._provider.generate_structured(
            messages=messages,
            schema=Stance,
            cache_name=cache_name,
            temperature=REFLECT_TEMP,
            thinking_disabled=True,
        )
        stance = result.parsed
        stance.cycle_id = cycle.cycle_id
        return stance
