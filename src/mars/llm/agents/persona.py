from mars.llm.prompts.debate import ASSESSMENT, build_debate_prompt
from mars.llm.prompts.persona import (
    PHASE_BY_TURN_TYPE,
    SYSTEM_PROMPT,
    TurnType,
    bullet_lines,
    constraints_block,
)
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import (
    AgentResponse,
    AgentTurn,
    DebateAssessment,
    EvidenceSet,
)
from mars.models.persona import Persona


CLAIM_LIMIT = 500
RATIONALE_LIMIT = 1400
MESSAGE_LIMIT = 500


def clip(text: str | None, limit: int) -> str | None:
    if text is None or len(text) <= limit:
        return text
    cut = text[:limit]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > limit * 0.6 else cut).strip()


def agent_lines(others: list[Persona]) -> str:
    if not others:
        return "No other agents."
    return "\n".join(
        f"- {a.name} [evidence: {a.evidence_relation}]: {a.framing}" for a in others
    )


def turn_log(turns: list[AgentTurn], names: dict[str, str] | None = None) -> str:
    if not turns:
        return ""
    names = names or {}
    lines = []
    for turn in turns:
        who = names.get(turn.agent_id, turn.agent_id)
        response = turn.response
        header = f"[{who} | {turn.phase}"
        if response.action:
            header += f" | {response.action.value}"
        if response.target_id:
            header += f" -> {names.get(response.target_id, response.target_id)}"
        header += "]"
        evidence = ", ".join(response.evidence) if response.evidence else "none"
        lines.append(
            f"{header}\nClaim: {response.claim}\nRationale: {response.rationale}\n"
            f"Message: {response.message}\nEvidence (corpus_ids): {evidence}"
        )
    return "\n\n".join(lines)


def turn_digest(turns: list[AgentTurn], names: dict[str, str] | None = None) -> str:
    if not turns:
        return ""
    names = names or {}
    lines = []
    for turn in turns:
        who = names.get(turn.agent_id, turn.agent_id)
        response = turn.response
        target = (
            f" -> {names.get(response.target_id, response.target_id)}"
            if response.target_id
            else ""
        )
        action = f" | {response.action.value}" if response.action else ""
        lines.append(
            f"[{who} | {turn.phase}{action}{target}] {response.claim} {response.message}"
        )
    return "\n".join(lines)


def evidence_block(bundle: EvidenceSet) -> str:
    if not bundle.snippets:
        return "No evidence available."
    blocks = []
    for snippet in bundle.snippets:
        section = f"Section: {snippet.section}\n" if snippet.section else ""
        blocks.append(
            f"Title: {snippet.title}\nCorpus ID: {snippet.corpus_id}\n"
            f"{section}Content: {snippet.text}"
        )
    return "\n\n===============\n\n".join(blocks)


def assessment_block(assessment: DebateAssessment) -> str:
    disagreements = bullet_lines(
        [f"{', '.join(d.agents)}: {d.point}" for d in assessment.points_of_disagreement]
    )
    critiques = bullet_lines(
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


def system_prompt(persona: Persona) -> str:
    return SYSTEM_PROMPT.format(
        name=persona.name,
        framing=persona.framing,
        background=persona.background,
        reasoning_style=persona.reasoning_style,
        evaluation_lens=persona.evaluation_lens,
        instructions=bullet_lines(persona.instructions),
        constraints=constraints_block(persona.constraints),
    )


class PersonaSpeaker:
    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def produce(
        self,
        *,
        persona: Persona,
        others: list[Persona],
        evidence: EvidenceSet,
        focal_claim: str,
        turn_type: TurnType,
        prior_turns: list[AgentTurn],
        cycle: int = 1,
        assessment: DebateAssessment | None = None,
        cache_name: str | None = None,
    ) -> tuple[AgentTurn, TokenUsage]:
        phase = PHASE_BY_TURN_TYPE[turn_type]
        names = {str(p.cluster_id): p.name for p in (persona, *others)}
        assessment_text = (
            assessment_block(assessment)
            if turn_type in ("respond", "refine") and assessment is not None
            else None
        )
        body = build_debate_prompt(
            phase,
            focal_claim,
            evidence_block(evidence),
            agent_lines(others),
            turn_digest(prior_turns, names),
            assessment_text,
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
            thinking_level="medium",
        )
        response = result.parsed
        if turn_type == "propose":
            response.evidence_weight = None
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
