import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from loguru import logger

from mars.client.s2 import SemanticScholarClient
from mars.llm.agents.critic import CriticAgent
from mars.llm.agents.judge import Judge
from mars.llm.agents.persona import (
    PersonaSpeaker,
    agent_lines,
    evidence_block,
    system_prompt,
)
from mars.llm.agents.scout import ScoutAgent
from mars.llm.prompts.debate import context_block
from mars.llm.prompts.persona import (
    PHASE_PROPOSAL,
    PHASE_REBUTTAL,
    PHASE_REFINEMENT,
    TurnType,
)
from mars.llm.providers.base import LLMProvider
from mars.models.debate import (
    ACTION_BY_WEIGHT,
    Cycle,
    Debate,
    DebateAssessment,
    EvidenceSet,
    EvidenceWeight,
    TurnAction,
)
from mars.models.persona import Persona
from mars.schemas.event import StageName
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext

dlog = logger.bind(source="workflow.debate", stage="debate")

CACHE_TTL_SECONDS = 600

DEBATE_TERMS = [
    r"debate",
    r"debaters?",
    r"debating",
    r"discussion",
    r"argues?",
    r"arguing",
    r"rebuts?",
    r"the (?:technologist|ethicist|researcher|scientist|linguist|theorist|economist|psychologist)",
]


class ReferenceChecker:
    FIELDS = ("problem", "previous_work", "reasoning", "hypothesis")

    def __init__(self, agent_names: list[str]) -> None:
        heads = [n.split("·")[0].strip() for n in agent_names]
        frags = [re.escape(h) for h in heads if len(h) >= 4]
        self._rx = re.compile(
            rf"\b(?:{'|'.join(DEBATE_TERMS + frags)})\b", re.IGNORECASE
        )

    def __call__(self, text: str) -> bool:
        return bool(self._rx.search(text or ""))

    def fields(self, meta) -> list[str]:
        return [f for f in self.FIELDS if self._rx.search(getattr(meta, f, "") or "")]


def cited_ids(cycle: Cycle, agent_id: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in cycle.turns:
        if t.agent_id != agent_id:
            continue
        for cid in t.response.evidence:
            if cid and cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


def last_claim(cycle: Cycle, agent_id: str) -> str:
    claim = ""
    for t in cycle.turns:
        if t.agent_id == agent_id:
            claim = t.response.claim
    return claim


def warn_on_action_collapse(cycle: Cycle, *, dominant_threshold: float = 0.8) -> None:
    actions = [
        turn.response.action for turn in cycle.turns if turn.response.action is not None
    ]
    if not actions:
        return

    total = len(actions)
    counts = Counter(actions)
    contest = counts.get(TurnAction.CHALLENGE, 0) + counts.get(TurnAction.CONCEDE, 0)

    if contest == 0:
        dlog.warning(
            "action | action collapse: 0 challenge/concede across {} turns (consensus round)",
            total,
        )
        return

    top_action, top_count = counts.most_common(1)[0]
    if top_count / total >= dominant_threshold:
        dlog.warning(
            "action | action collapse: {} is {}/{} of turns",
            top_action.value,
            top_count,
            total,
        )


def warn_on_unrelated_share(cycle: Cycle, *, unrelated_threshold: float = 0.4) -> None:
    weights = [
        turn.response.evidence_weight
        for turn in cycle.turns
        if turn.response.evidence_weight is not None
    ]
    if not weights:
        return
    total = len(weights)
    unrelated = Counter(weights).get(EvidenceWeight.UNRELATED, 0)
    if unrelated / total >= unrelated_threshold:
        dlog.warning(
            "weight | unrelated share high: {}/{} turns "
            "(possible off-axis dodge; inspect messages vs labels)",
            unrelated,
            total,
        )


_ADVERSARIAL_OPENER = re.compile(
    r"^\s*[^,.]{2,40},\s+(your|you)\b.*\b("
    r"ignore|ignores|ignoring|fail|fails|overlook|overlooks|wrong|"
    r"cannot|can't|does\s+not|doesn't)\b",
    re.IGNORECASE,
)
_REVISION_OPENER = re.compile(
    r"^\s*(i\s+(revise|concede|narrow|accept|grant|withdraw)|on reflection|i now|i no longer)\b",
    re.IGNORECASE,
)
_DISPUTE_MARKERS = re.compile(
    r"\b(interpret|interpretation|misread|conflate|conflates|"
    r"scope|generaliz|overstate|overstates|does not show|"
    r"valid|validity|confound|artifact|measure|measures|operationaliz)\w*\b",
    re.IGNORECASE,
)
_MISMATCH_MARKERS = re.compile(
    r"\b(different|differs|separate|distinct|other|another|"
    r"mechanism|population|domain|scope|setting|context|task|modality|"
    r"does not bear|not about|off-?topic|orthogonal)\w*\b",
    re.IGNORECASE,
)


def validate_turn(resp) -> list[str]:
    errors: list[str] = []
    if resp.action is TurnAction.CONCEDE:
        if not resp.conceded_point:
            errors.append("concede: conceded_point is required")
        if not resp.revised_position:
            errors.append("concede: revised_position is required")
        msg = resp.message or ""
        if _ADVERSARIAL_OPENER.match(msg):
            errors.append("concede: message opens by attacking the opponent")
        if not _REVISION_OPENER.match(msg):
            errors.append("concede: message does not open with the revision")
    elif resp.conceded_point or resp.preserved_point or resp.revised_position:
        errors.append(
            f"{resp.action.value if resp.action else 'non-concede'}: concession fields must be null"
        )

    if resp.evidence_weight is EvidenceWeight.DISPUTED:
        if not _DISPUTE_MARKERS.search(resp.message or ""):
            errors.append(
                "disputed: message does not name what it contests (interpretation/scope/validity)"
            )
    elif resp.evidence_weight is EvidenceWeight.UNRELATED:
        if not _MISMATCH_MARKERS.search(resp.message or ""):
            errors.append(
                "unrelated: message does not name the mechanism/population/scope mismatch"
            )

    return errors


def rebuild_concede_message(resp) -> str:
    parts = [f"I revise: {resp.conceded_point.rstrip('.')}."]
    if resp.preserved_point:
        parts.append(f"I still hold {resp.preserved_point.rstrip('.')}.")
    parts.append(f"My position is now: {resp.revised_position.rstrip('.')}.")
    return " ".join(parts)


@dataclass(frozen=True, slots=True)
class DebateNodeConfig:
    debate_retrieval: bool = True
    counter_evidence: bool = False
    proposal: bool = True
    assessment: bool = True
    rebuttal: bool = True
    refinement: bool = True
    adjudication: bool = True
    synthesis: bool = True
    select_best: bool = True
    compose: bool = True


class DebateRuntime:
    def __init__(
        self,
        *,
        llm: LLMProvider,
        s2: SemanticScholarClient,
        judge_llm: LLMProvider | None = None,
        retrieval_filters: dict | None = None,
        debate_retrieval: bool = True,
        counter_evidence: bool = False,
    ) -> None:
        self._llm = llm
        self._persona_agent = PersonaSpeaker(provider=llm)
        self._judge = Judge(provider=judge_llm or llm)
        self._scout = ScoutAgent(s2=s2, provider=llm)
        self._critic = CriticAgent(provider=judge_llm or llm)
        self._retrieval_filters = retrieval_filters or {}
        self._debate_retrieval = debate_retrieval
        self._counter_evidence = counter_evidence
        self._caches: dict[str, dict[str, str]] = {}

    async def prepare(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        agents = ctx.debate.agents
        self._caches[cycle.cycle_id] = {}
        cluster_papers = {
            str(cid): papers for cid, papers in (ctx.clusters or {}).items()
        }

        async def prep(agent: Persona) -> None:
            agent_id = str(agent.cluster_id)
            cluster_ids = [p.id for p in cluster_papers.get(agent_id, [])]
            bundle, _ = await self._scout.for_persona(
                agent_id=agent_id,
                framing=agent.framing,
                focal_claim=cycle.focal_claim,
                claim=cycle.focal_claim,
                cluster_paper_ids=cluster_ids,
                secondary_filters=self._retrieval_filters,
            )
            cycle.evidence[agent_id] = bundle
            others = [a for a in agents if a != agent]
            content = context_block(
                cycle.focal_claim, evidence_block(bundle), agent_lines(others)
            )
            try:
                name = await self._llm.create_cache(
                    system_instruction=system_prompt(agent),
                    content=content,
                    ttl_seconds=CACHE_TTL_SECONDS,
                )
                self._caches[cycle.cycle_id][agent_id] = name
            except Exception as exc:
                dlog.warning("cache creation failed for agent {}: {}", agent_id, exc)

        await asyncio.gather(*(prep(a) for a in agents))

    async def _turn(
        self,
        ctx: WorkflowContext,
        persona: Persona,
        turn_type: TurnType,
        assessment: DebateAssessment | None = None,
    ):
        cycle = ctx.cycle
        agents = ctx.debate.agents
        agent_id = str(persona.cluster_id)
        others = [a for a in agents if a != persona]
        evidence = cycle.evidence.get(agent_id, EvidenceSet())
        cache_name = self._caches.get(cycle.cycle_id, {}).get(agent_id)

        for attempt in range(2):
            try:
                turn, call_usage = await self._persona_agent.produce(
                    persona=persona,
                    others=others,
                    evidence=evidence,
                    focal_claim=cycle.focal_claim,
                    turn_type=turn_type,
                    prior_turns=cycle.turns,
                    cycle=cycle.cycle,
                    assessment=assessment,
                    cache_name=cache_name,
                )
            except Exception as exc:
                if attempt == 0:
                    dlog.debug("{} agent {} retry: {}", turn_type, agent_id, exc)
                    continue
                dlog.warning("{} agent {} dropped: {}", turn_type, agent_id, exc)
                return None
            if turn.response.evidence_weight is not None:
                turn.response.action = ACTION_BY_WEIGHT[turn.response.evidence_weight]
                dlog.info(
                    "weight | {} agent {} evidence_weight={} -> action={}",
                    turn_type,
                    agent_id,
                    turn.response.evidence_weight.value,
                    turn.response.action.value,
                )
                errors = validate_turn(turn.response)
                if errors and attempt == 0:
                    dlog.debug(
                        "coherence | {} agent {} retrying: {}",
                        turn_type,
                        agent_id,
                        errors,
                    )
                    continue
                if errors:
                    resp = turn.response
                    if (
                        resp.action is TurnAction.CONCEDE
                        and resp.conceded_point
                        and resp.revised_position
                    ):
                        resp.message = rebuild_concede_message(resp)
                        dlog.warning(
                            "coherence | {} agent {} concede message rebuilt from fields",
                            turn_type,
                            agent_id,
                        )
                    elif resp.action is not TurnAction.CONCEDE:
                        resp.conceded_point = resp.preserved_point = (
                            resp.revised_position
                        ) = None
                    else:
                        dlog.warning(
                            "coherence | {} agent {} concede missing fields after retry",
                            turn_type,
                            agent_id,
                        )
            dlog.info(
                "turn.produced | {} agent {} -> claim len {} [{}]",
                turn_type,
                agent_id,
                len(turn.response.claim or ""),
                call_usage,
            )
            return turn
        return None

    async def propose(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        proposals = await asyncio.gather(
            *(self._turn(ctx, a, "propose") for a in ctx.debate.agents)
        )
        cycle.turns.extend(t for t in proposals if t is not None)

    async def assess(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        assessment, _ = await self._judge.assess(
            focal_claim=cycle.focal_claim,
            agents=ctx.debate.agents,
            turns=cycle.turns,
            cycle=cycle.cycle,
        )
        cycle.assessment = assessment
        if not assessment.disagreement_present:
            dlog.warning("assess | consensus collapse: disagreement_present=False")

    async def rebut(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        rebuttals = await asyncio.gather(
            *(
                self._turn(ctx, a, "respond", cycle.assessment)
                for a in ctx.debate.agents
            )
        )
        cycle.turns.extend(t for t in rebuttals if t is not None)

    async def refine(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        refinements = await asyncio.gather(
            *(self._turn(ctx, a, "refine", cycle.assessment) for a in ctx.debate.agents)
        )
        cycle.turns.extend(t for t in refinements if t is not None)

    async def adjudicate(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        conflict = (
            cycle.assessment.central_conflict if cycle.assessment else cycle.focal_claim
        )
        if self._debate_retrieval:
            for agent_id in cycle.agent_ids:
                if agent_id in cycle.judge_evidence:
                    continue
                bundle, _ = await self._scout.for_judge(
                    agent_id=agent_id,
                    agent_claim=last_claim(cycle, agent_id),
                    central_conflict=conflict,
                    agent_cited_ids=cited_ids(cycle, agent_id),
                )
                cycle.judge_evidence[agent_id] = bundle
        if self._counter_evidence and self._debate_retrieval:
            await self._counter(cycle)
        adjudication, _ = await self._judge.adjudicate(
            research_query=cycle.problem,
            focal_claim=cycle.focal_claim,
            central_conflict=conflict,
            agents=ctx.debate.agents,
            turns=cycle.turns,
            evidence=cycle.judge_evidence,
            counterclaims=cycle.counter or None,
            cycle=cycle.cycle,
        )
        cycle.adjudication = adjudication

    async def _counter(self, cycle: Cycle) -> None:
        async def one(agent_id: str) -> None:
            claim = last_claim(cycle, agent_id)
            if not claim:
                return
            decomp, _ = await self._critic.decompose(
                claim=claim, central_conflict=cycle.focal_claim
            )
            internal_seed = cited_ids(cycle, agent_id)
            external_seed = [
                cid
                for other in cycle.agent_ids
                if other != agent_id
                for cid in cited_ids(cycle, other)
            ]
            internal, external = await self._scout.for_counter(
                counter_queries=decomp.counter_queries,
                internal_seed_ids=internal_seed,
                external_seed_ids=external_seed,
            )
            counterclaim, _ = await self._critic.classify(
                decomposition=decomp, internal=internal, external=external
            )
            cycle.counter[agent_id] = counterclaim
            cycle.counter_evidence[agent_id] = EvidenceSet(
                snippets=internal.snippets + external.snippets
            )

        await asyncio.gather(*(one(a) for a in cycle.agent_ids))

    async def summarize(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        warn_on_action_collapse(cycle)
        warn_on_unrelated_share(cycle)
        synthesis, _ = await self._judge.summarize(
            focal_claim=cycle.focal_claim,
            agents=ctx.debate.agents,
            turns=cycle.turns,
            adjudication=cycle.adjudication,
            cycle=cycle.cycle,
        )
        cycle.synthesis = synthesis
        if not synthesis.hypotheses:
            dlog.warning("summarize | no candidates; skipping selection and compose")
        await self._ground_relations(cycle)

    async def _ground_relations(self, cycle: Cycle) -> None:
        if not cycle.synthesis:
            return
        conflict = (
            cycle.assessment.central_conflict if cycle.assessment else cycle.focal_claim
        )
        for h in cycle.synthesis.hypotheses:
            if not h.is_relational:
                h.relation_grounding = []
                continue
            if not self._debate_retrieval:
                h.relation_grounding = []
                continue
            bundle, _ = await self._scout.for_relation(
                relation_claim=h.statement,
                central_conflict=conflict,
                mechanism_ids=h.grounding,
            )
            h.relation_grounding = list(
                dict.fromkeys(s.corpus_id for s in bundle.snippets)
            )
            dlog.info(
                "relation | {} relation_grounding={}/{} mechanism ids",
                h.id,
                len(h.relation_grounding),
                len(h.grounding),
            )

    async def select_best(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        if not cycle.synthesis or not cycle.synthesis.hypotheses:
            return
        checker = ReferenceChecker([a.name for a in ctx.debate.agents])
        central_conflict = (
            cycle.assessment.central_conflict if cycle.assessment else cycle.focal_claim
        )
        unresolved = cycle.adjudication.unresolved if cycle.adjudication else []
        choice = None
        for attempt in range(2):
            _, choice, _ = await self._judge.select_best(
                central_conflict=central_conflict,
                unresolved=unresolved,
                candidates=cycle.synthesis.hypotheses,
                cycle=cycle.cycle,
            )
            if not checker(choice.reason):
                break
            if attempt == 1:
                choice.reason = ""
        cycle.synthesis.best = choice

    async def compose(self, ctx: WorkflowContext) -> None:
        cycle = ctx.cycle
        if not cycle.synthesis or not cycle.synthesis.hypotheses:
            return
        candidates = cycle.synthesis.hypotheses
        by_id = {h.id: h for h in candidates}
        best_ref = cycle.synthesis.best
        best = (by_id.get(best_ref.candidate_id) if best_ref else None) or candidates[0]
        checker = ReferenceChecker([a.name for a in ctx.debate.agents])
        meta = None
        for _ in range(3):
            meta, _ = await self._judge.synthesize(
                focal_claim=cycle.focal_claim,
                problem=cycle.problem,
                assessment=cycle.assessment,
                adjudication=cycle.adjudication,
                candidates=candidates,
                best=best,
                cycle_obj=cycle,
                cycle=cycle.cycle,
            )
            if not checker.fields(meta):
                break
        cycle.synthesis.meta_review = meta

    async def destroy_caches(self, cycle_id: str) -> None:
        caches = self._caches.pop(cycle_id, {})
        if caches:
            await asyncio.gather(
                *(self._llm.delete_cache(name) for name in caches.values()),
                return_exceptions=True,
            )


class _RuntimeStep(BaseStep):
    def __init__(self, runtime: DebateRuntime, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self._rt = runtime


class PrepareEvidenceStep(_RuntimeStep):
    name = "debate.prepare_evidence"
    event = "debate.prepared"
    requires = ()

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.prepare(ctx)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"evidence": len(ctx.cycle.evidence)}


class ProposalStep(_RuntimeStep):
    name = "debate.proposal"
    event = "turn.produced"
    requires = ()

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.propose(ctx)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "proposals": sum(1 for t in ctx.cycle.turns if t.phase == PHASE_PROPOSAL)
        }


class AssessmentStep(_RuntimeStep):
    name = "debate.assessment"
    event = "cycle.assessed"
    requires = ("debate.proposal",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.assess(ctx)
        return ctx


class RebuttalStep(_RuntimeStep):
    name = "debate.rebuttal"
    event = "turn.produced"
    requires = ("debate.proposal",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.rebut(ctx)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "rebuttals": sum(1 for t in ctx.cycle.turns if t.phase == PHASE_REBUTTAL)
        }


class RefinementStep(_RuntimeStep):
    name = "debate.refinement"
    event = "turn.produced"
    requires = ("debate.proposal",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.refine(ctx)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "refinements": sum(
                1 for t in ctx.cycle.turns if t.phase == PHASE_REFINEMENT
            )
        }


class AdjudicationStep(_RuntimeStep):
    name = "debate.adjudication"
    event = "cycle.adjudicated"
    requires = ("debate.proposal",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.adjudicate(ctx)
        return ctx


class SynthesisStep(_RuntimeStep):
    name = "debate.synthesis"
    event = "cycle.synthesized"
    requires = ("debate.proposal",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.summarize(ctx)
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        syn = ctx.cycle.synthesis
        return {"candidates": len(syn.hypotheses) if syn else 0}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        syn = ctx.cycle.synthesis
        return f"{len(syn.hypotheses) if syn else 0} candidates"


class SelectBestStep(_RuntimeStep):
    name = "debate.select_best"
    event = "debate.best_selected"
    requires = ("debate.synthesis",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.select_best(ctx)
        return ctx


class ComposeStep(_RuntimeStep):
    name = "debate.compose"
    event = "debate.composed"
    requires = ("debate.synthesis",)

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        await self._rt.compose(ctx)
        return ctx

    def log_message(self, ctx: WorkflowContext) -> str | None:
        syn = ctx.cycle.synthesis
        return "meta-review composed" if syn and syn.meta_review else None


class DebateNode(BaseNode):
    def __init__(
        self,
        *,
        llm: LLMProvider,
        s2: SemanticScholarClient,
        judge_llm: LLMProvider | None = None,
        retrieval_filters: dict | None = None,
        config: DebateNodeConfig | None = None,
    ) -> None:
        cfg = config or DebateNodeConfig()
        self._runtime = DebateRuntime(
            llm=llm,
            s2=s2,
            judge_llm=judge_llm,
            retrieval_filters=retrieval_filters,
            debate_retrieval=cfg.debate_retrieval,
            counter_evidence=cfg.counter_evidence,
        )
        rt = self._runtime
        steps = [
            PrepareEvidenceStep(rt, enabled=cfg.debate_retrieval),
            ProposalStep(rt, enabled=cfg.proposal),
            AssessmentStep(rt, enabled=cfg.assessment),
            RebuttalStep(rt, enabled=cfg.rebuttal),
            RefinementStep(rt, enabled=cfg.refinement),
            AdjudicationStep(rt, enabled=cfg.adjudication),
            SynthesisStep(rt, enabled=cfg.synthesis),
            SelectBestStep(rt, enabled=cfg.select_best),
            ComposeStep(rt, enabled=cfg.compose),
        ]
        super().__init__(stage=StageName.DEBATE, name="debate", steps=steps)

    async def before_run(self, ctx: WorkflowContext) -> WorkflowContext:
        agents = ctx.personas
        cycle = Cycle(
            focal_claim=ctx.extracted.claim,
            problem=ctx.raw_text,
            agent_ids=[str(a.cluster_id) for a in agents],
        )
        ctx.debate = Debate(focal_claim=ctx.extracted.claim, agents=agents, cycle=cycle)
        ctx.cycle = cycle
        cycle.status = "running"
        return ctx

    async def after_run(self, ctx: WorkflowContext) -> WorkflowContext:
        if ctx.cycle is not None:
            await self._runtime.destroy_caches(ctx.cycle.cycle_id)
            ctx.cycle.status = "complete"
            if ctx.cycle.synthesis:
                ctx.debate.hypotheses = list(ctx.cycle.synthesis.hypotheses)
        return ctx

    async def on_error(self, ctx: WorkflowContext, exc: Exception) -> None:
        if ctx.cycle is not None:
            await self._runtime.destroy_caches(ctx.cycle.cycle_id)
        return None

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        syn = ctx.cycle.synthesis if ctx.cycle else None
        return {
            "turns": len(ctx.cycle.turns) if ctx.cycle else 0,
            "hypotheses": len(syn.hypotheses) if syn else 0,
        }
