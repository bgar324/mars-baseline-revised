from mars.llm.agents.persona import render_agents, render_turns
from mars.llm.prompts.judge import (
    ADJUDICATION_PROMPT,
    ASSESSMENT_PROMPT,
    HYPOTHESIS_PROMPT,
    JUDGE_SYSTEM,
    SELECT_PROMPT,
    SELECT_SYSTEM,
    SYNTHESIS_PROMPT,
    SYNTHESIS_SYSTEM,
)
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import (
    Adjudication,
    AgentTurn,
    BestCandidate,
    DebateAssessment,
    EvidenceSet,
    Hypothesis,
    MetaReview,
    Synthesis,
)
from mars.models.persona import PersonaAgent as PersonaModel


def render_adjudication(adjudication: Adjudication) -> str:
    resolved = "\n".join(f"- {r}" for r in adjudication.resolved) or "- none"
    unresolved = "\n".join(f"- {u}" for u in adjudication.unresolved) or "- none"
    return (
        f"Reasoning: {adjudication.reasoning}\n\n"
        f"Resolved:\n{resolved}\n\nUnresolved:\n{unresolved}"
    )


def render_cross_exam(
    evidence: dict[str, EvidenceSet], names: dict[str, str]
) -> str:
    if not evidence:
        return "No cross-examination evidence retrieved."
    blocks = []
    for agent_id, bundle in evidence.items():
        who = names.get(agent_id, agent_id)
        if not bundle.snippets:
            blocks.append(f"## {who}\nNo passages found in this agent's cited papers.")
            continue
        passages = "\n".join(
            f"- [corpus_id {s.corpus_id}] {s.text}" for s in bundle.snippets
        )
        blocks.append(f"## {who}\n{passages}")
    return "\n\n".join(blocks)


def render_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- none"


def render_candidates(candidates: list[Hypothesis]) -> str:
    return "\n".join(f"[{h.id}] {h.statement}" for h in candidates) or "- none"


def render_positions(candidates: list[Hypothesis]) -> str:
    return "\n".join(f"- {c.statement.strip()}" for c in candidates)


def render_candidate(best: Hypothesis) -> str:
    v = best.variables
    return (
        f"[{best.id}] {best.statement}\n"
        f"mechanism: {best.mechanism}\n"
        f"variables: IV={v.independent}; DV={v.dependent}; "
        f"moderators={v.moderators or 'none'}; mediators={v.mediators or 'none'}\n"
        f"scope: {best.scope}\n"
        f"falsifier: {best.falsifier}"
    )


def render_evidence(cycle) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for evset in list(cycle.evidence.values()) + list(cycle.judge_evidence.values()):
        for s in evset.snippets:
            if s.corpus_id in seen:
                continue
            seen.add(s.corpus_id)
            finding = (s.text or "").strip().replace("\n", " ")
            if len(finding) > 320:
                finding = finding[:320].rsplit(" ", 1)[0] + "…"
            title = f" ({s.title})" if s.title else ""
            lines.append(f"- {finding}{title} [{s.corpus_id}]")
    return "\n".join(lines) if lines else "- none"


class Judge:
    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def assess(
        self,
        *,
        focal_claim: str,
        agents: list[PersonaModel],
        turns: list[AgentTurn],
        cycle: int = 1,
    ) -> tuple[DebateAssessment, TokenUsage]:
        names = {str(a.cluster_id): a.name for a in agents}
        user = ASSESSMENT_PROMPT.format(
            agents=render_agents(agents),
            focal_claim=focal_claim,
            turns=render_turns(turns, names),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=DebateAssessment,
            thinking_level="high",
        )
        assessment = result.parsed
        assessment.phase = "assessment"
        assessment.cycle = cycle
        return assessment, result.usage

    async def adjudicate(
        self,
        *,
        focal_claim: str,
        central_conflict: str,
        agents: list[PersonaModel],
        turns: list[AgentTurn],
        evidence: dict[str, EvidenceSet] | None = None,
        cycle: int = 1,
    ) -> tuple[Adjudication, TokenUsage]:
        names = {str(a.cluster_id): a.name for a in agents}
        user = ADJUDICATION_PROMPT.format(
            focal_claim=focal_claim,
            central_conflict=central_conflict,
            turns=render_turns(turns, names),
            cross_examination=render_cross_exam(evidence or {}, names),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=Adjudication,
            thinking_level="high",
        )
        adjudication = result.parsed
        adjudication.phase = "adjudication"
        adjudication.cycle = cycle
        return adjudication, result.usage

    async def summarize(
        self,
        *,
        focal_claim: str,
        agents: list[PersonaModel],
        turns: list[AgentTurn],
        adjudication: Adjudication,
        cycle: int = 1,
    ) -> tuple[Synthesis, TokenUsage]:
        names = {str(a.cluster_id): a.name for a in agents}
        user = HYPOTHESIS_PROMPT.format(
            focal_claim=focal_claim,
            turns=render_turns(turns, names),
            adjudication=render_adjudication(adjudication),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=Synthesis,
            thinking_level="low",
        )
        synthesis = result.parsed
        synthesis.phase = "synthesis"
        synthesis.cycle = cycle
        for index, hypothesis in enumerate(synthesis.hypotheses):
            hypothesis.id = f"H{index + 1}"
        return synthesis, result.usage

    async def select_best(
        self,
        *,
        central_conflict: str,
        unresolved: list[str],
        candidates: list[Hypothesis],
        cycle: int = 1,
    ) -> tuple[Hypothesis, BestCandidate, TokenUsage]:
        user = SELECT_PROMPT.format(
            central_conflict=central_conflict,
            unresolved=render_list(unresolved),
            candidates=render_candidates(candidates),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SELECT_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=BestCandidate,
            thinking_level="high",
        )
        choice = result.parsed
        by_id = {h.id: h for h in candidates}
        best = by_id.get(choice.candidate_id) or candidates[0]
        return best, choice, result.usage

    async def synthesize(
        self,
        *,
        focal_claim: str,
        problem: str,
        assessment: DebateAssessment,
        adjudication: Adjudication,
        candidates: list[Hypothesis],
        best: Hypothesis,
        cycle_obj,
        cycle: int = 1,
    ) -> tuple[MetaReview, TokenUsage]:
        user = SYNTHESIS_PROMPT.format(
            focal_claim=focal_claim,
            problem=problem,
            central_conflict=assessment.central_conflict,
            positions=render_positions(candidates),
            evidence=render_evidence(cycle_obj),
            settled=render_list(adjudication.resolved),
            contested=render_list(adjudication.unresolved),
            best=render_candidate(best),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM},
                {"role": "user", "content": user},
            ],
            schema=MetaReview,
            thinking_level="high",
        )
        meta = result.parsed
        meta.best_id = best.id
        return meta, result.usage
