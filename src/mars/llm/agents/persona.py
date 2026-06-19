from mars.llm.prompts.debate import ASSESSMENT, build_debate_prompt
from mars.llm.prompts.persona import (
    SYSTEM_PROMPT,
    TurnType,
    format_constraints,
    format_list,
)
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import (
    AgentResponse,
    AgentTurn,
    DebateAssessment,
    EvidenceSet,
)
from mars.models.persona import PersonaAgent as PersonaModel


PHASE: dict[str, str] = {
    "propose": "proposal",
    "respond": "rebuttal",
    "refine": "refutation",
}

CLAIM_LIMIT = 500
RATIONALE_LIMIT = 1400
MESSAGE_LIMIT = 500


def clip(text: str | None, limit: int) -> str | None:
    if text is None or len(text) <= limit:
        return text
    cut = text[:limit]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > limit * 0.6 else cut).strip()


def render_agents(others: list[PersonaModel]) -> str:
    if not others:
        return "No other agents."
    return "\n".join(f"- {a.name}: {a.framing}" for a in others)


def render_turns(turns: list[AgentTurn], names: dict[str, str] | None = None) -> str:
    if not turns:
        return ""
    names = names or {}
    rendered = []
    for t in turns:
        who = names.get(t.agent_id, t.agent_id)
        r = t.response
        header = f"[{who} | {t.phase}"
        if r.action:
            header += f" | {r.action}"
        if r.target_id:
            header += f" -> {names.get(r.target_id, r.target_id)}"
        header += "]"
        evidence = ", ".join(r.evidence) if r.evidence else "none"
        rendered.append(
            f"{header}\nClaim: {r.claim}\nRationale: {r.rationale}\n"
            f"Message: {r.message}\nEvidence (corpus_ids): {evidence}"
        )
    return "\n\n".join(rendered)


def render_evidence(bundle: EvidenceSet) -> str:
    if not bundle.snippets:
        return "No evidence available."
    blocks = []
    for s in bundle.snippets:
        section = f"Section: {s.section}\n" if s.section else ""
        blocks.append(
            f"Title: {s.title}\n"
            f"Corpus ID: {s.corpus_id}\n"
            f"{section}"
            f"Content: {s.text}"
        )
    return "\n\n===============\n\n".join(blocks)


def render_assessment(assessment: DebateAssessment) -> str:
    disagreements = format_list(
        [f"{', '.join(d.agents)}: {d.point}" for d in assessment.points_of_disagreement]
    )
    critiques = format_list(
        [
            f"{c.challenger or 'any'} presses {c.target}: {c.on_point}"
            for c in assessment.critiques
        ]
    )
    return ASSESSMENT.format(
        central_conflict=assessment.central_conflict,
        disagreements=disagreements,
        critiques=critiques,
    )


def system_prompt(persona: PersonaModel) -> str:
    return SYSTEM_PROMPT.format(
        name=persona.name,
        framing=persona.framing,
        background=persona.background,
        reasoning_style=persona.reasoning_style,
        evaluation_lens=persona.evaluation_lens,
        instructions=format_list(persona.instructions),
        constraints=format_constraints(persona.constraints),
    )


class PersonaTurnAgent:
    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def produce(
        self,
        *,
        persona: PersonaModel,
        others: list[PersonaModel],
        evidence: EvidenceSet,
        focal_claim: str,
        turn_type: TurnType,
        prior_turns: list[AgentTurn],
        cycle: int = 1,
        assessment: DebateAssessment | None = None,
        cache_name: str | None = None,
    ) -> tuple[AgentTurn, TokenUsage]:
        phase = PHASE[turn_type]
        names = {str(p.cluster_id): p.name for p in (persona, *others)}
        assessment_block = (
            render_assessment(assessment)
            if turn_type in ("respond", "refine") and assessment is not None
            else None
        )
        body = build_debate_prompt(
            phase,
            focal_claim,
            render_evidence(evidence),
            render_agents(others),
            render_turns(prior_turns, names),
            assessment_block,
            evidence_present=bool(evidence.snippets),
            include_context=cache_name is None,
        )
        if cache_name is not None:
            messages = [{"role": "user", "content": body}]
        else:
            messages = [
                {"role": "system", "content": system_prompt(persona)},
                {"role": "user", "content": body},
            ]

        result = await self._provider.generate_structured(
            messages=messages,
            schema=AgentResponse,
            cache_name=cache_name,
            thinking_level="high",
        )
        response = result.parsed
        if turn_type == "propose":
            response.action = None
            response.target_id = None
        response.claim = clip(response.claim, CLAIM_LIMIT)
        response.rationale = clip(response.rationale, RATIONALE_LIMIT)
        response.message = clip(response.message, MESSAGE_LIMIT)

        turn = AgentTurn(
            agent_id=str(persona.cluster_id),
            phase=phase,
            cycle=cycle,
            response=response,
        )
        return turn, result.usage
