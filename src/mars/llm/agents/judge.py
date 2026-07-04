from mars.llm.agents.persona import agent_lines, turn_log
from mars.llm.prompts.judge import (
    ADJUDICATION_PROMPT,
    ASSESSMENT_PROMPT,
    HYPOTHESIS_PROMPT,
    SELECT_PROMPT,
    SYNTHESIS_PROMPT,
    SYSTEM_PROMPT,
)
from mars.llm.prompts.persona import bullet_lines
from mars.llm.providers.base import LLMProvider, TokenUsage
from mars.models.debate import (
    Adjudication,
    AgentTurn,
    BestCandidate,
    Counterclaim,
    DebateAssessment,
    EvidenceSet,
    Hypothesis,
    MetaReview,
    Synthesis,
)
from mars.models.persona import Persona


def agent_names(agents: list[Persona]) -> dict[str, str]:
    return {str(agent.cluster_id): agent.name for agent in agents}


def adjudication_block(adjudication: Adjudication) -> str:
    resolved = bullet_lines(adjudication.resolved, empty="- none")
    unresolved = bullet_lines(adjudication.unresolved, empty="- none")
    return (
        f"Reasoning: {adjudication.reasoning}\n\n"
        f"Resolved:\n{resolved}\n\nUnresolved:\n{unresolved}"
    )


def counterclaim_lines(counterclaims: dict[str, Counterclaim] | None) -> str:
    if not counterclaims:
        return "None."
    lines = []
    for counterclaim in counterclaims.values():
        if counterclaim.verdict.status == "rejected":
            continue
        scope = (
            f"; scope: {counterclaim.verdict.scope}"
            if counterclaim.verdict.scope
            else ""
        )
        lines.append(
            f"- [{counterclaim.verdict.status}] {counterclaim.decomposition.counterclaim} "
            f"(weakness: {counterclaim.decomposition.weakness}{scope})"
        )
    return "\n".join(lines) or "None."


def cross_exam_block(
    evidence: dict[str, EvidenceSet],
    names: dict[str, str],
    relations: dict[str, str] | None = None,
) -> str:
    if not evidence:
        return "No cross-examination evidence retrieved."
    relations = relations or {}
    blocks = []
    for agent_id, bundle in evidence.items():
        who = names.get(agent_id, agent_id)
        relation = relations.get(agent_id)
        header = f"## {who} [evidence: {relation}]" if relation else f"## {who}"
        if not bundle.snippets:
            blocks.append(f"{header}\nNo passages found in this agent's cited papers.")
            continue
        passages = "\n".join(
            f"- [corpus_id {snippet.corpus_id}] {snippet.text}"
            for snippet in bundle.snippets
        )
        blocks.append(f"{header}\n{passages}")
    return "\n\n".join(blocks)


def candidate_lines(candidates: list[Hypothesis]) -> str:
    lines = []
    for hypothesis in candidates:
        design = hypothesis.study_design
        lines.append(
            f"[{hypothesis.id}] {hypothesis.proposition} "
            f"(type: {hypothesis.claim_type}; comparator: {design.comparator}; "
            f"measure: {design.measure})"
        )
    return "\n".join(lines) or "- none"


def hypothesis_lines(candidates: list[Hypothesis]) -> str:
    return "\n".join(f"- {candidate.proposition.strip()}" for candidate in candidates)


def candidate_detail(best: Hypothesis) -> str:
    design = best.study_design
    return (
        f"[{best.id}] {best.proposition}\n"
        f"claim_type: {best.claim_type}\n"
        f"causal_chain: {best.causal_chain}\n"
        f"study_design: context={design.context}; exposure={design.exposure}; "
        f"comparator={design.comparator}; outcome={design.outcome}; measure={design.measure}\n"
        f"warrant: {best.warrant}\n"
        f"falsifier: {best.falsifier}"
    )


def evidence_digest(cycle) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for evidence in list(cycle.evidence.values()) + list(cycle.judge_evidence.values()):
        for snippet in evidence.snippets:
            if snippet.corpus_id in seen:
                continue
            seen.add(snippet.corpus_id)
            finding = (snippet.text or "").strip().replace("\n", " ")
            if len(finding) > 320:
                finding = finding[:320].rsplit(" ", 1)[0] + "…"
            title = f" ({snippet.title})" if snippet.title else ""
            lines.append(f"- {finding}{title} [{snippet.corpus_id}]")
    return "\n".join(lines) if lines else "- none"


class Judge:
    def __init__(self, *, provider: LLMProvider) -> None:
        self._provider = provider

    async def assess(
        self,
        *,
        focal_claim: str,
        agents: list[Persona],
        turns: list[AgentTurn],
        cycle: int = 1,
    ) -> tuple[DebateAssessment, TokenUsage]:
        names = agent_names(agents)
        user = ASSESSMENT_PROMPT.format(
            agents=agent_lines(agents),
            focal_claim=focal_claim,
            turns=turn_log(turns, names),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
        research_query: str,
        focal_claim: str,
        central_conflict: str,
        agents: list[Persona],
        turns: list[AgentTurn],
        evidence: dict[str, EvidenceSet] | None = None,
        counterclaims: dict[str, Counterclaim] | None = None,
        cycle: int = 1,
    ) -> tuple[Adjudication, TokenUsage]:
        names = agent_names(agents)
        relations = {str(a.cluster_id): a.evidence_relation for a in agents}
        user = ADJUDICATION_PROMPT.format(
            research_query=research_query,
            focal_claim=focal_claim,
            central_conflict=central_conflict,
            turns=turn_log(turns, names),
            cross_examination=cross_exam_block(evidence or {}, names, relations),
            counterclaims=counterclaim_lines(counterclaims),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
        agents: list[Persona],
        turns: list[AgentTurn],
        adjudication: Adjudication | None = None,
        cycle: int = 1,
    ) -> tuple[Synthesis, TokenUsage]:
        names = agent_names(agents)
        user = HYPOTHESIS_PROMPT.format(
            focal_claim=focal_claim,
            turns=turn_log(turns, names),
            adjudication=(
                adjudication_block(adjudication)
                if adjudication
                else "No adjudication was performed."
            ),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            schema=Synthesis,
            thinking_level="medium",
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
        research_query: str,
        central_conflict: str,
        unresolved: list[str],
        candidates: list[Hypothesis],
        cycle: int = 1,
    ) -> tuple[Hypothesis, BestCandidate, TokenUsage]:
        user = SELECT_PROMPT.format(
            research_query=research_query,
            central_conflict=central_conflict,
            unresolved=bullet_lines(unresolved, empty="- none"),
            candidates=candidate_lines(candidates),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            schema=BestCandidate,
            thinking_level="medium",
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
        assessment: DebateAssessment | None = None,
        adjudication: Adjudication | None = None,
        candidates: list[Hypothesis],
        best: Hypothesis,
        cycle_obj,
        cycle: int = 1,
    ) -> tuple[MetaReview, TokenUsage]:
        user = SYNTHESIS_PROMPT.format(
            focal_claim=focal_claim,
            problem=problem,
            central_conflict=(
                assessment.central_conflict if assessment else focal_claim
            ),
            candidates=hypothesis_lines(candidates),
            evidence=evidence_digest(cycle_obj),
            resolved=bullet_lines(
                adjudication.resolved if adjudication else [], empty="- none"
            ),
            unresolved=bullet_lines(
                adjudication.unresolved if adjudication else [], empty="- none"
            ),
            best=candidate_detail(best),
        )
        result = await self._provider.generate_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            schema=MetaReview,
            thinking_level="high",
        )
        meta = result.parsed
        meta.best_id = best.id
        return meta, result.usage
