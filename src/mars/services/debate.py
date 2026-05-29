import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import numpy as np

from mars.client.s2 import SemanticScholarClient
from mars.llm.agents.judge import Judge
from mars.llm.agents.persona import (
    PersonaTurnAgent,
    build_debate_context,
    build_system_prompt,
)
from mars.llm.providers.base import EmbeddingProvider, LLMProvider
from mars.models.debate import (
    AgentState,
    AgentTurn,
    Branch,
    Cycle,
    Debate,
    DebateDecision,
    Stance,
    Steer,
    TurnType,
)
from mars.models.persona import PersonaAgent as PersonaModel
from mars.models.s2 import Paper
from mars.schemas.event import DebateEvent, DebateEventType

logger = logging.getLogger(__name__)


class DebateError(Exception):
    """Base error for debate operations."""


class NotFoundError(DebateError):
    """Raised when a debate, cycle, or agent state does not exist."""


class StateError(DebateError):
    """Raised when an operation is invalid for the current cycle status."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


COVERAGE_THRESHOLD = 0.5
EXPANSION_CAP = 3
EVIDENCE_K = 5
RECOMMENDATIONS_LIMIT = 10
CACHE_TTL_SECONDS = 3600


class DebateService:
    """Runs a debate: agents take turns, a judge synthesizes, the researcher steers."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
        s2: SemanticScholarClient,
        judge_llm: LLMProvider | None = None,
    ) -> None:
        self._llm = llm
        self._persona_agent = PersonaTurnAgent(provider=llm)
        self._judge = Judge(provider=judge_llm or llm)
        self._embedder = embedder
        self._s2 = s2
        self._debates: dict[str, Debate] = {}
        self._agent_states: dict[str, dict[str, AgentState]] = {}
        self._cluster_papers: dict[str, dict[str, list[Paper]]] = {}
        self._cycle_caches: dict[str, dict[str, str]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[DebateEvent]]] = {}

    async def start(
        self,
        *,
        focal_claim: str,
        agents: list[PersonaModel],
        cluster_papers: dict[str, list[Paper]] | None = None,
    ) -> Debate:
        debate = Debate(root_focal_claim=focal_claim, agents=agents)
        self._debates[debate.debate_id] = debate
        self._agent_states[debate.debate_id] = {
            str(a.cluster_id): AgentState(agent_id=str(a.cluster_id)) for a in agents
        }
        self._cluster_papers[debate.debate_id] = cluster_papers or {}
        self._subscribers[debate.debate_id] = set()

        root = Cycle(
            focal_claim=focal_claim,
            agent_ids=[str(a.cluster_id) for a in agents],
        )
        debate.cycles[root.cycle_id] = root
        await self._emit(debate.debate_id, DebateEventType.DEBATE_STARTED)
        return debate

    async def run_cycle(self, *, debate_id: str, cycle_id: str) -> Cycle:
        debate = self._require_debate(debate_id)
        cycle = debate.cycles.get(cycle_id)
        if cycle is None:
            raise NotFoundError(f"cycle {cycle_id} not found")
        if cycle.status != "pending":
            raise StateError(f"cycle {cycle_id} is {cycle.status}, not pending")

        agents = [a for a in debate.agents if str(a.cluster_id) in cycle.agent_ids]
        if not agents:
            raise StateError(
                f"cycle {cycle_id} has no agents matching agent_ids {cycle.agent_ids}"
            )

        cycle.status = "running"
        cycle.updated_at = _now()
        await self._emit(debate_id, DebateEventType.CYCLE_STARTED, cycle_id=cycle_id)

        recap = self._build_recap(debate, cycle)

        try:
            await self._create_caches(debate_id, cycle, agents, recap)

            proposals = await asyncio.gather(
                *(
                    self._produce(debate_id, cycle, a, agents, "propose", recap)
                    for a in agents
                )
            )
            cycle.turns.extend(proposals)

            for agent in agents:
                turn = await self._produce(
                    debate_id, cycle, agent, agents, "respond", recap
                )
                cycle.turns.append(turn)

            refinements = await asyncio.gather(
                *(
                    self._produce(debate_id, cycle, a, agents, "refine", recap)
                    for a in agents
                )
            )
            cycle.turns.extend(refinements)

            cycle.synthesis = await self._judge.synthesize(cycle=cycle, agents=agents)
            await self._emit(
                debate_id, DebateEventType.CYCLE_SYNTHESIZED, cycle_id=cycle_id
            )

            stances = await asyncio.gather(
                *(self._reflect(debate_id, cycle, a) for a in agents)
            )
            for agent, stance in zip(agents, stances):
                agent_id = str(agent.cluster_id)
                state = self._agent_states[debate_id][agent_id]
                state.stance = stance
                state.history.extend([t for t in cycle.turns if t.agent_id == agent_id])
                await self._emit(
                    debate_id,
                    DebateEventType.STANCE_UPDATED,
                    cycle_id=cycle_id,
                    agent_id=agent_id,
                )

            cycle.status = "awaiting"
            cycle.updated_at = _now()
            await self._emit(
                debate_id, DebateEventType.CYCLE_AWAITING, cycle_id=cycle_id
            )
            return cycle
        finally:
            await self._destroy_caches(cycle.cycle_id)

    async def steer(self, *, debate_id: str, decision: DebateDecision) -> Cycle | None:
        debate = self._require_debate(debate_id)
        cycle = debate.cycles.get(decision.cycle_id)
        if cycle is None:
            raise NotFoundError(f"cycle {decision.cycle_id} not found")
        if cycle.status != "awaiting":
            raise StateError(
                f"cycle {decision.cycle_id} is {cycle.status}, not awaiting"
            )

        if decision.action == "accept":
            if not decision.hypothesis:
                raise StateError("accept requires hypothesis")
            debate.hypotheses.append(decision.hypothesis)
            await self._emit(
                debate_id,
                DebateEventType.HYPOTHESIS_ACCEPTED,
                cycle_id=decision.cycle_id,
                hypothesis=decision.hypothesis,
            )
            return None

        if decision.action == "close":
            cycle.status = "complete"
            await self._emit(
                debate_id, DebateEventType.CYCLE_CLOSED, cycle_id=cycle.cycle_id
            )
            return None

        if decision.action == "branch":
            if not decision.branch:
                raise StateError("branch requires Branch payload")
            return await self._create_child(debate, cycle, decision.branch)

        raise StateError(f"unknown action {decision.action}")

    async def set_steers(
        self, *, debate_id: str, cycle_id: str, steers: list[Steer]
    ) -> Cycle:
        debate = self._require_debate(debate_id)
        cycle = debate.cycles.get(cycle_id)
        if cycle is None:
            raise NotFoundError(f"cycle {cycle_id} not found")
        if cycle.status not in {"pending", "awaiting"}:
            raise StateError(
                f"cycle {cycle_id} is {cycle.status}; cannot set steers"
            )
        cycle.steers = steers
        cycle.updated_at = _now()
        return cycle

    async def propose(
        self,
        *,
        debate_id: str,
        cycle_id: str,
        agent_id: str,
        steers: list[Steer] | None = None,
    ) -> AgentTurn:
        debate = self._require_debate(debate_id)
        cycle = debate.cycles.get(cycle_id)
        if cycle is None:
            raise NotFoundError(f"cycle {cycle_id} not found")
        if agent_id not in cycle.agent_ids:
            raise NotFoundError(f"agent {agent_id} not in cycle {cycle_id}")
        persona = next(
            (a for a in debate.agents if str(a.cluster_id) == agent_id), None
        )
        if persona is None:
            raise NotFoundError(f"agent {agent_id} not in debate {debate_id}")

        others = [
            a
            for a in debate.agents
            if str(a.cluster_id) in cycle.agent_ids and str(a.cluster_id) != agent_id
        ]
        evidence = await self._retrieve(debate_id, agent_id, cycle.focal_claim)
        return await self._persona_agent.produce(
            persona=persona,
            cycle=cycle,
            others=others,
            prior_turns=[],
            turn_type="propose",
            evidence=evidence,
            recap=None,
            cache_name=None,
            steers=steers or [],
        )

    def get_debate(self, debate_id: str) -> Debate:
        return self._require_debate(debate_id)

    def get_cycle(self, debate_id: str, cycle_id: str) -> Cycle:
        debate = self._require_debate(debate_id)
        cycle = debate.cycles.get(cycle_id)
        if cycle is None:
            raise NotFoundError(f"cycle {cycle_id} not found")
        return cycle

    def get_agent_state(self, debate_id: str, agent_id: str) -> AgentState:
        states = self._agent_states.get(debate_id)
        if states is None or agent_id not in states:
            raise NotFoundError(f"agent state for {agent_id} not found")
        return states[agent_id]

    def _require_debate(self, debate_id: str) -> Debate:
        debate = self._debates.get(debate_id)
        if debate is None:
            raise NotFoundError(f"debate {debate_id} not found")
        return debate

    def _build_recap(self, debate: Debate, cycle: Cycle) -> str | None:
        if not cycle.parent_cycle_id:
            return None
        parent = debate.cycles[cycle.parent_cycle_id]
        if not parent.synthesis:
            return None
        s = parent.synthesis
        parts = [f"Parent focal claim: {parent.focal_claim}"]
        if s.points_of_agreement:
            parts.append("Agreed: " + "; ".join(s.points_of_agreement[:2]))
        if s.points_of_disagreement:
            parts.append("Disagreed: " + "; ".join(s.points_of_disagreement[:2]))
        return "\n".join(parts)

    def _resolve_agent_ids(
        self, debate: Debate, requested: list[str] | None
    ) -> list[str]:
        """Map requested agent identifiers (ids or persona names) to agent_ids."""
        if not requested:
            return []
        by_id = {str(a.cluster_id) for a in debate.agents}
        by_name = {a.name: str(a.cluster_id) for a in debate.agents}
        resolved: list[str] = []
        for item in requested:
            key = str(item)
            agent_id = key if key in by_id else by_name.get(key)
            if agent_id and agent_id not in resolved:
                resolved.append(agent_id)
        return resolved

    async def _create_child(
        self,
        debate: Debate,
        parent: Cycle,
        branch: Branch,
    ) -> Cycle:
        agent_ids = self._resolve_agent_ids(debate, branch.agents) or parent.agent_ids
        for agent in debate.agents:
            if str(agent.cluster_id) in agent_ids:
                await self._maybe_expand(debate, agent, branch.focal_claim)
        child = Cycle(
            parent_cycle_id=parent.cycle_id,
            focal_claim=branch.focal_claim,
            agent_ids=agent_ids,
        )
        debate.cycles[child.cycle_id] = child
        await self._emit(
            debate.debate_id,
            DebateEventType.CYCLE_BRANCHED,
            cycle_id=child.cycle_id,
            parent_cycle_id=parent.cycle_id,
        )
        return child

    async def _produce(
        self,
        debate_id: str,
        cycle: Cycle,
        persona: PersonaModel,
        all_agents: list[PersonaModel],
        turn_type: TurnType,
        recap: str | None,
    ) -> AgentTurn:
        agent_id = str(persona.cluster_id)
        cache_name = self._cycle_caches.get(cycle.cycle_id, {}).get(agent_id)
        evidence: list[Paper] = []
        if cache_name is None:
            evidence = await self._retrieve(debate_id, agent_id, cycle.focal_claim)
        others = [a for a in all_agents if a != persona]
        turn = await self._persona_agent.produce(
            persona=persona,
            cycle=cycle,
            others=others,
            prior_turns=cycle.turns,
            turn_type=turn_type,
            evidence=evidence,
            recap=recap,
            cache_name=cache_name,
            steers=cycle.steers,
        )
        await self._emit(
            debate_id,
            DebateEventType.TURN_PRODUCED,
            cycle_id=cycle.cycle_id,
            turn=turn.model_dump(mode="json"),
            turn_id=turn.turn_id,
            agent_id=turn.agent_id,
            turn_type=turn_type,
        )
        return turn

    async def _reflect(
        self, debate_id: str, cycle: Cycle, agent: PersonaModel
    ) -> Stance:
        agent_id = str(agent.cluster_id)
        own_turns = [t for t in cycle.turns if t.agent_id == agent_id]
        prior = self._agent_states[debate_id][agent_id].stance
        cache_name = self._cycle_caches.get(cycle.cycle_id, {}).get(agent_id)
        return await self._persona_agent.reflect(
            persona=agent,
            cycle=cycle,
            own_turns=own_turns,
            prior_stance=prior,
            cache_name=cache_name,
        )

    async def _create_caches(
        self,
        debate_id: str,
        cycle: Cycle,
        agents: list[PersonaModel],
        recap: str | None,
    ) -> None:
        """Cache each agent's stable prompt prefix for the cycle."""
        self._cycle_caches[cycle.cycle_id] = {}

        async def make(agent: PersonaModel) -> None:
            agent_id = str(agent.cluster_id)
            others = [a for a in agents if a != agent]
            evidence = await self._retrieve(debate_id, agent_id, cycle.focal_claim)
            system = build_system_prompt(agent)
            context = build_debate_context(cycle, others, evidence, recap)
            try:
                name = await self._llm.create_cache(
                    system_instruction=system,
                    content=context,
                    ttl_seconds=CACHE_TTL_SECONDS,
                )
            except Exception as exc:
                logger.warning("cache creation failed for agent %s: %s", agent_id, exc)
                return
            self._cycle_caches[cycle.cycle_id][agent_id] = name

        await asyncio.gather(*(make(a) for a in agents))

    async def _destroy_caches(self, cycle_id: str) -> None:
        caches = self._cycle_caches.pop(cycle_id, {})
        if caches:
            await asyncio.gather(
                *(self._llm.delete_cache(name) for name in caches.values()),
                return_exceptions=True,
            )

    async def _retrieve(
        self, debate_id: str, agent_id: str, query: str, k: int = EVIDENCE_K
    ) -> list[Paper]:
        """The agent's cluster papers most relevant to the query."""
        papers = self._cluster_papers[debate_id].get(agent_id, [])
        embedded = [p for p in papers if p.specter_v2 is not None]
        if not embedded:
            return []
        query_vec = await self._embedder.embed(query)
        matrix = np.array([p.specter_v2 for p in embedded], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vec)
        scores = (matrix @ query_vec) / (norms + 1e-9)
        top = scores.argsort()[-k:][::-1]
        return [embedded[i] for i in top]

    async def _coverage(self, debate_id: str, agent_id: str, query: str) -> float:
        """How well the agent's cluster covers the query, from 0 to 1."""
        papers = self._cluster_papers[debate_id].get(agent_id, [])
        embedded = [p for p in papers if p.specter_v2 is not None]
        if not embedded:
            return 0.0
        query_vec = await self._embedder.embed(query)
        matrix = np.array([p.specter_v2 for p in embedded], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vec)
        scores = (matrix @ query_vec) / (norms + 1e-9)
        return float(scores.max())

    async def _maybe_expand(
        self, debate: Debate, agent: PersonaModel, focal_claim: str
    ) -> None:
        """Pull in fresh papers when the agent's cluster stops covering the claim."""
        agent_id = str(agent.cluster_id)
        state = self._agent_states[debate.debate_id][agent_id]
        if state.expansions >= EXPANSION_CAP:
            return

        coverage = await self._coverage(debate.debate_id, agent_id, focal_claim)
        if coverage >= COVERAGE_THRESHOLD:
            return

        cluster = self._cluster_papers[debate.debate_id]
        positives = [p.id for p in cluster.get(agent_id, []) if p.id]
        if not positives:
            return
        negatives = [
            p.id
            for other in debate.agents
            if other != agent
            for p in cluster.get(str(other.cluster_id), [])
            if p.id
        ]
        new_papers = await self._s2.recommendations(
            positive_paper_ids=positives,
            negative_paper_ids=negatives,
            limit=RECOMMENDATIONS_LIMIT,
        )
        cluster.setdefault(agent_id, []).extend(new_papers)
        state.expansions += 1
        await self._emit(
            debate.debate_id,
            DebateEventType.CORPUS_EXPANDED,
            agent_id=agent_id,
            papers_added=len(new_papers),
        )

    async def _emit(
        self,
        debate_id: str,
        event: DebateEventType,
        *,
        cycle_id: str | None = None,
        **payload: Any,
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
