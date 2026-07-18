import asyncio
from unittest.mock import MagicMock

from mars.models.debate import AgentResponse, AgentTurn, Cycle, Debate
from mars.models.persona import Persona
from mars.schemas.event import EventType
from mars.session_cache import SessionCache
from mars.workflow.base import WorkflowContext
from mars.workflow.debate import DebateRuntime, turn_payload
from mars.workflow.pipeline import Pipeline


# --------------------------------------------------------------------------
# session cache: no database, short-lived cross-request snapshots
# --------------------------------------------------------------------------


class _FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.writes: list[tuple[str, object, dict | None]] = []

    async def get(self, key: str) -> object:
        return self.values.get(key)

    async def set(self, key: str, value: object, options: dict | None = None) -> None:
        self.values[key] = value
        self.writes.append((key, value, options))


def _state_and_ctx():
    pipeline = Pipeline(nodes=[])
    state = pipeline.create_query("A problem", "manual", "baseline")
    return state, pipeline.get_context(state.query_id)


def test_session_cache_writes_latest_snapshot_with_ttl() -> None:
    backend = _FakeCache()
    cache = SessionCache(backend, ttl_seconds=120)
    state, ctx = _state_and_ctx()

    async def go():
        await cache.upsert_session(
            state=state, ctx=ctx, backend_snapshot={"n": 1}, wait=True
        )
        await cache.upsert_session(state=state, ctx=ctx, backend_snapshot={"n": 2})

    asyncio.run(go())

    assert backend.values[state.query_id] == {"n": 2}
    assert backend.writes[-1] == (state.query_id, {"n": 2}, {"ttl": 120})


def test_load_session_returns_cached_backend_snapshot() -> None:
    backend = _FakeCache()
    backend.values["query-1"] = {"query_id": "query-1", "state": {}}
    cache = SessionCache(backend)

    async def go():
        snapshot = await cache.load_session("query-1")
        missing = await cache.load_session("missing")
        return snapshot, missing

    snapshot, missing = asyncio.run(go())
    assert snapshot == {"query_id": "query-1", "state": {}}
    assert missing is None


# --------------------------------------------------------------------------
# debate: per-agent thinking/turn events + incremental transcript
# --------------------------------------------------------------------------


def _persona(cluster_id: int) -> Persona:
    return Persona(
        cluster_id=cluster_id,
        references=[],
        methods_summary="Methods",
        evidence_relation="direct",
        name=f"Researcher {cluster_id}",
        role="Methodologist",
        perspective="Evidence quality.",
        framing="Frame",
        background="Background",
        reasoning_style="mechanistic",
        evaluation_lens="internal_validity",
        instructions=["Argue from evidence.", "Stay scoped.", "Name limits."],
    )


def _stub_turn(agent_id: str) -> AgentTurn:
    return AgentTurn(
        agent_id=agent_id,
        phase="proposal",
        response=AgentResponse(claim="c", rationale="r", message="m", evidence=["42"]),
    )


def test_proposal_phase_streams_per_agent_events_and_appends_incrementally() -> None:
    agents = [_persona(1), _persona(2)]
    cycle = Cycle(focal_claim="claim", problem="problem", agent_ids=["1", "2"])
    ctx = WorkflowContext(
        query_id="q",
        raw_text="problem",
        condition="baseline",
        personas=agents,
        debate=Debate(focal_claim="claim", agents=agents, cycle=cycle),
        cycle=cycle,
    )

    events: list[tuple] = []

    async def sink(event, *, stage=None, step=None, payload=None):
        events.append((event, payload))

    ctx.emit = sink

    runtime = DebateRuntime(llm=MagicMock(), s2=MagicMock())

    async def fake_turn(_ctx, persona, _turn_type, _assessment=None):
        # Simulate the turn arriving as soon as the model finishes.
        return _stub_turn(str(persona.cluster_id))

    runtime._turn = fake_turn  # type: ignore[assignment]

    asyncio.run(runtime.propose(ctx))

    # Both turns landed in the transcript.
    assert len(cycle.turns) == 2
    assert {t.agent_id for t in cycle.turns} == {"1", "2"}

    thinking = [e for e in events if e[0] is EventType.AGENT_THINKING]
    turns = [e for e in events if e[0] is EventType.AGENT_TURN]
    assert len(thinking) == 2
    assert len(turns) == 2
    # thinking events name the agent + phase for the UI.
    assert {e[1]["agent_id"] for e in thinking} == {"1", "2"}
    assert all(e[1]["phase"] == "proposal" for e in thinking)
    # turn events carry the rendered contribution.
    assert all(e[1]["message"] == "m" and e[1]["evidence"] == ["42"] for e in turns)


def test_turn_payload_shape() -> None:
    payload = turn_payload(_persona(3), _stub_turn("3"))
    assert payload["agent_id"] == "3"
    assert payload["agent_name"] == "Researcher 3"
    assert payload["phase"] == "proposal"
    assert payload["claim"] == "c"
    assert payload["evidence"] == ["42"]
