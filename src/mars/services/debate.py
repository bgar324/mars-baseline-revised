import asyncio
import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from mars.client.s2 import SemanticScholarClient
from mars.llm.agents.judge import Judge
from mars.llm.agents.persona import (
    PersonaTurnAgent,
    render_agents,
    render_evidence,
    system_prompt,
)
from mars.llm.agents.scout import ScoutAgent
from mars.llm.prompts.debate import render_context
from mars.llm.prompts.persona import TurnType
from mars.llm.providers.base import LLMProvider
from mars.models.debate import AgentTurn, Cycle, Debate, DebateAssessment, EvidenceSet
from mars.models.persona import PersonaAgent as PersonaModel
from mars.models.s2 import Paper
from mars.schemas.event import DebateEvent, DebateEventType
from mars.utils.debate_log import RunUsage, log

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600


class DebateError(Exception): ...


class NotFoundError(DebateError): ...


class StateError(DebateError): ...


DEBATE_TERMS = [
    r"debate", r"debaters?", r"debating", r"discussion", r"argues?", r"arguing", r"rebuts?",
    r"the (?:technologist|ethicist|researcher|scientist|linguist|theorist|economist|psychologist)",
]


class ReferenceChecker:
    FIELDS = ("problem", "previous_work", "reasoning", "hypothesis")

    def __init__(self, agent_names: list[str]) -> None:
        heads = [n.split("·")[0].strip() for n in agent_names]
        frags = [re.escape(h) for h in heads if len(h) >= 4]
        self._rx = re.compile(rf"\b(?:{'|'.join(DEBATE_TERMS + frags)})\b", re.IGNORECASE)

    def __call__(self, text: str) -> bool:
        return bool(self._rx.search(text or ""))

    def fields(self, meta) -> list[str]:
        return [f for f in self.FIELDS if self._rx.search(getattr(meta, f, "") or "")]


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def phase_seen(cycle: Cycle, phase: str) -> bool:
    return any(t.phase == phase for t in cycle.turns)


class DebateService:
    def __init__(
        self,
        *,
        llm: LLMProvider,
        s2: SemanticScholarClient,
        judge_llm: LLMProvider | None = None,
        retrieval_filters: dict | None = None,
    ) -> None:
        self._llm = llm
        self._persona_agent = PersonaTurnAgent(provider=llm)
        self._judge = Judge(provider=judge_llm or llm)
        self._scout = ScoutAgent(s2=s2, provider=llm)
        self._s2 = s2
        self._retrieval_filters = retrieval_filters or {}
        self._debates: dict[str, Debate] = {}
        self._cluster_papers: dict[str, dict[str, list[Paper]]] = {}
        self._caches: dict[str, dict[str, str]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[DebateEvent]]] = {}

    async def start(
        self,
        *,
        focal_claim: str,
        agents: list[PersonaModel],
        cluster_papers: dict[str, list[Paper]] | None = None,
        problem: str | None = None,
    ) -> Debate:
        cycle = Cycle(
            focal_claim=focal_claim,
            problem=problem or focal_claim,
            agent_ids=[str(a.cluster_id) for a in agents],
        )
        debate = Debate(focal_claim=focal_claim, agents=agents, cycle=cycle)
        self._debates[debate.debate_id] = debate
        self._cluster_papers[debate.debate_id] = cluster_papers or {}
        self._subscribers[debate.debate_id] = set()
        await self._emit(debate.debate_id, DebateEventType.DEBATE_STARTED)
        return debate

    async def run_cycle(
        self, *, debate_id: str, cycle_id: str, usage: RunUsage | None = None
    ) -> Cycle:
        debate = self._require_debate(debate_id)
        cycle = debate.cycle
        if cycle is None or cycle.cycle_id != cycle_id:
            raise NotFoundError(f"cycle {cycle_id} not found")
        if cycle.status == "complete":
            return cycle
        if cycle.status not in ("pending", "running"):
            raise StateError(f"cycle {cycle_id} is {cycle.status}, cannot run")

        agents = [a for a in debate.agents if str(a.cluster_id) in cycle.agent_ids]
        if not agents:
            raise StateError(f"cycle {cycle_id} has no matching agents")

        usage = usage or RunUsage()
        start = usage.snapshot()
        resuming = cycle.status == "running" or bool(cycle.turns)
        cycle.status = "running"
        cycle.updated_at = _now()
        verb = "resume" if resuming else "start"
        log("INFO", "debate", verb, "run_cycle", f"{len(agents)} agents, cycle {cycle.cycle}")
        await self._emit(debate_id, DebateEventType.CYCLE_STARTED, cycle_id=cycle_id)

        try:
            if not cycle.evidence:
                await self._prepare(debate_id, cycle, agents, usage)

            if not phase_seen(cycle, "proposal"):
                proposals = await asyncio.gather(
                    *(self._turn(debate_id, cycle, a, agents, "propose", usage) for a in agents)
                )
                cycle.turns.extend(t for t in proposals if t is not None)

            if cycle.assessment is None:
                cycle.assessment = await self._assess(debate_id, cycle, agents, usage)

            if not phase_seen(cycle, "rebuttal"):
                for agent in agents:
                    turn = await self._turn(
                        debate_id, cycle, agent, agents, "respond", usage, cycle.assessment
                    )
                    if turn is not None:
                        cycle.turns.append(turn)

            if not phase_seen(cycle, "refutation"):
                refinements = await asyncio.gather(
                    *(
                        self._turn(debate_id, cycle, a, agents, "refine", usage, cycle.assessment)
                        for a in agents
                    )
                )
                cycle.turns.extend(t for t in refinements if t is not None)

            if cycle.adjudication is None:
                cycle.adjudication = await self._adjudicate(debate_id, cycle, agents, usage)
            if cycle.synthesis is None:
                cycle.synthesis = await self._summarize(debate_id, cycle, agents, usage)
            if cycle.synthesis.hypotheses and cycle.synthesis.best is None:
                cycle.synthesis.best = await self._select_best(debate_id, cycle, usage)
            if cycle.synthesis.hypotheses and cycle.synthesis.meta_review is None:
                cycle.synthesis.meta_review = await self._compose(debate_id, cycle, usage)
            debate.hypotheses = list(cycle.synthesis.hypotheses)
        finally:
            await self._destroy_caches(cycle.cycle_id)

        cycle.status = "complete"
        cycle.updated_at = _now()
        log(
            "INFO",
            "debate",
            "done",
            "run_cycle",
            f"{len(cycle.turns)} turns, {len(cycle.synthesis.hypotheses)} hypotheses "
            f"[stage total {usage.since(start)}]",
        )
        return cycle

    def get_debate(self, debate_id: str) -> Debate:
        return self._require_debate(debate_id)

    def get_cycle(self, debate_id: str, cycle_id: str) -> Cycle:
        debate = self._require_debate(debate_id)
        if debate.cycle is None or debate.cycle.cycle_id != cycle_id:
            raise NotFoundError(f"cycle {cycle_id} not found")
        return debate.cycle

    def _require_debate(self, debate_id: str) -> Debate:
        debate = self._debates.get(debate_id)
        if debate is None:
            raise NotFoundError(f"debate {debate_id} not found")
        return debate

    async def _prepare(
        self, debate_id: str, cycle: Cycle, agents: list[PersonaModel], usage: RunUsage
    ) -> None:
        self._caches[cycle.cycle_id] = {}

        async def prep(agent: PersonaModel) -> None:
            nonlocal usage
            agent_id = str(agent.cluster_id)
            cluster_ids = [p.id for p in self._cluster_papers[debate_id].get(agent_id, [])]
            bundle, call_usage = await self._scout.for_persona(
                agent_id=agent_id,
                framing=agent.framing,
                focal_claim=cycle.focal_claim,
                claim=cycle.focal_claim,
                cluster_paper_ids=cluster_ids,
                secondary_filters=self._retrieval_filters,
            )
            cycle.evidence[agent_id] = bundle
            usage += call_usage

            others = [a for a in agents if a != agent]
            content = render_context(
                cycle.focal_claim, render_evidence(bundle), render_agents(others)
            )
            try:
                name = await self._llm.create_cache(
                    system_instruction=system_prompt(agent),
                    content=content,
                    ttl_seconds=CACHE_TTL_SECONDS,
                )
                self._caches[cycle.cycle_id][agent_id] = name
            except Exception as exc:
                logger.warning("debate cache creation failed for agent %s: %s", agent_id, exc)

        await asyncio.gather(*(prep(a) for a in agents))

    async def _destroy_caches(self, cycle_id: str) -> None:
        caches = self._caches.pop(cycle_id, {})
        if caches:
            await asyncio.gather(
                *(self._llm.delete_cache(name) for name in caches.values()),
                return_exceptions=True,
            )

    async def _turn(
        self,
        debate_id: str,
        cycle: Cycle,
        persona: PersonaModel,
        agents: list[PersonaModel],
        turn_type: TurnType,
        usage: RunUsage,
        assessment: DebateAssessment | None = None,
    ) -> AgentTurn | None:
        agent_id = str(persona.cluster_id)
        others = [a for a in agents if a != persona]
        evidence = cycle.evidence.get(agent_id, EvidenceSet())
        cache_name = self._caches.get(cycle.cycle_id, {}).get(agent_id)
        log("INFO", "debate", "call", turn_type, f"agent {agent_id} ({persona.name})")

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
                    log("WARN", "debate", "warn", turn_type, f"agent {agent_id} retry: {exc}")
                    continue
                log("WARN", "debate", "warn", turn_type, f"agent {agent_id} dropped: {exc}")
                return None
            usage += call_usage
            if not turn.response.claim or not turn.response.message:
                log("WARN", "debate", "warn", turn_type, f"agent {agent_id} empty field")
            log(
                "INFO",
                "debate",
                "parsed",
                turn_type,
                f"agent {agent_id} → claim len {len(turn.response.claim or '')} "
                f"[{call_usage}]",
            )
            await self._emit(
                debate_id,
                DebateEventType.TURN_PRODUCED,
                cycle_id=cycle.cycle_id,
                turn_id=turn.turn_id,
                agent_id=turn.agent_id,
                phase=turn.phase,
            )
            return turn
        return None

    async def _assess(
        self,
        debate_id: str,
        cycle: Cycle,
        agents: list[PersonaModel],
        usage: RunUsage,
    ) -> DebateAssessment:
        log("INFO", "debate", "call", "assess", "mapping the terrain")
        assessment, call_usage = await self._judge.assess(
            focal_claim=cycle.focal_claim, agents=agents, turns=cycle.turns, cycle=cycle.cycle
        )
        usage += call_usage
        if not assessment.disagreement_present:
            log("WARN", "debate", "warn", "assess", "consensus collapse: disagreement_present=False")
        log(
            "INFO",
            "debate",
            "parsed",
            "assess",
            f"central_conflict set, disagreement_present={assessment.disagreement_present} "
            f"[{call_usage}]",
        )
        await self._emit(debate_id, DebateEventType.CYCLE_ASSESSED, cycle_id=cycle.cycle_id)
        return assessment

    async def _adjudicate(
        self,
        debate_id: str,
        cycle: Cycle,
        agents: list[PersonaModel],
        usage: RunUsage,
    ):
        conflict = cycle.assessment.central_conflict if cycle.assessment else cycle.focal_claim

        for agent_id in cycle.agent_ids:
            if agent_id in cycle.judge_evidence:
                continue
            bundle, call_usage = await self._scout.for_judge(
                agent_id=agent_id,
                agent_claim=last_claim(cycle, agent_id),
                central_conflict=conflict,
                agent_cited_ids=cited_ids(cycle, agent_id),
            )
            cycle.judge_evidence[agent_id] = bundle
            usage += call_usage

        log("INFO", "debate", "call", "adjudicate", "reasoning over transcript")
        adjudication, call_usage = await self._judge.adjudicate(
            focal_claim=cycle.focal_claim,
            central_conflict=conflict,
            agents=agents,
            turns=cycle.turns,
            evidence=cycle.judge_evidence,
            cycle=cycle.cycle,
        )
        usage += call_usage
        log(
            "INFO",
            "debate",
            "parsed",
            "adjudicate",
            f"{len(adjudication.resolved)} resolved, {len(adjudication.unresolved)} unresolved "
            f"[{call_usage}]",
        )
        await self._emit(debate_id, DebateEventType.CYCLE_ADJUDICATED, cycle_id=cycle.cycle_id)
        return adjudication

    async def _summarize(
        self,
        debate_id: str,
        cycle: Cycle,
        agents: list[PersonaModel],
        usage: RunUsage,
    ):
        log("INFO", "debate", "call", "summarize", "emitting candidates")
        synthesis, call_usage = await self._judge.summarize(
            focal_claim=cycle.focal_claim,
            agents=agents,
            turns=cycle.turns,
            adjudication=cycle.adjudication,
            cycle=cycle.cycle,
        )
        usage += call_usage
        ungrounded = sum(1 for h in synthesis.hypotheses if not h.grounding)
        if ungrounded:
            log("WARN", "debate", "warn", "summarize", f"{ungrounded} candidates with empty grounding")
        if not synthesis.hypotheses:
            log("WARN", "debate", "warn", "summarize", "no candidates; skipping selection and compose")
        log(
            "INFO",
            "debate",
            "parsed",
            "summarize",
            f"{len(synthesis.hypotheses)} candidates [{call_usage}]",
        )
        await self._emit(debate_id, DebateEventType.CYCLE_SYNTHESIZED, cycle_id=cycle.cycle_id)
        return synthesis

    async def _select_best(self, debate_id: str, cycle: Cycle, usage: RunUsage):
        checker = ReferenceChecker([a.name for a in self._require_debate(debate_id).agents])
        log("INFO", "debate", "call", "select_best", "choosing the unresolved-crux candidate")
        best = None
        choice = None
        call_usage = None
        for attempt in range(2):
            best, choice, call_usage = await self._judge.select_best(
                central_conflict=cycle.assessment.central_conflict,
                unresolved=cycle.adjudication.unresolved,
                candidates=cycle.synthesis.hypotheses,
                cycle=cycle.cycle,
            )
            usage += call_usage
            if not checker(choice.reason):
                break
            if attempt == 0:
                log("WARN", "debate", "warn", "select_best", "reason leaked process/role language — regenerating")
            else:
                log("WARN", "debate", "warn", "select_best", "reason leak persists — blanking why for the researcher surface")
                choice.reason = ""
        log(
            "INFO",
            "debate",
            "parsed",
            "select_best",
            f"best={best.id} ({choice.reason[:60]}) [{call_usage}]",
        )
        return choice

    async def _compose(self, debate_id: str, cycle: Cycle, usage: RunUsage):
        candidates = cycle.synthesis.hypotheses
        by_id = {h.id: h for h in candidates}
        best = by_id.get(cycle.synthesis.best.candidate_id) or candidates[0]
        checker = ReferenceChecker([a.name for a in self._require_debate(debate_id).agents])
        log("INFO", "debate", "call", "synthesize", f"composing four-step on {best.id}")

        meta = None
        call_usage = None
        for attempt in range(3):
            meta, call_usage = await self._judge.synthesize(
                focal_claim=cycle.focal_claim,
                problem=cycle.problem,
                assessment=cycle.assessment,
                adjudication=cycle.adjudication,
                candidates=candidates,
                best=best,
                cycle_obj=cycle,
                cycle=cycle.cycle,
            )
            usage += call_usage
            leaks = checker.fields(meta)
            if not leaks:
                break
            tail = "regenerating" if attempt < 2 else "persists after retries, shipping"
            log("WARN", "debate", "warn", "synthesize", f"meta_review leak in {leaks} — {tail}")

        log(
            "INFO",
            "debate",
            "parsed",
            "synthesize",
            f"meta_review built on {best.id} [{call_usage}]",
        )
        return meta

    async def _emit(
        self,
        debate_id: str,
        event: DebateEventType,
        *,
        cycle_id: str | None = None,
        **payload,
    ) -> None:
        evt = DebateEvent(
            event=event,
            debate_id=debate_id,
            cycle_id=cycle_id,
            payload=payload,
            timestamp=_now(),
        )
        for queue in list(self._subscribers.get(debate_id, ())):
            await queue.put(evt)

    async def subscribe(self, debate_id: str) -> AsyncIterator[DebateEvent]:
        self._require_debate(debate_id)
        queue: asyncio.Queue[DebateEvent] = asyncio.Queue()
        self._subscribers.setdefault(debate_id, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.get(debate_id, set()).discard(queue)
