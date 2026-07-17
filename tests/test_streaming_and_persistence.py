import asyncio
from unittest.mock import MagicMock

import mars.db.study as study_mod
from mars.config.settings import SupabaseSettings
from mars.db.study import StudySessionRecorder
from mars.models.debate import AgentResponse, AgentTurn, Cycle, Debate
from mars.models.persona import Persona
from mars.schemas.event import EventType
from mars.workflow.base import WorkflowContext
from mars.workflow.debate import DebateRuntime, turn_payload
from mars.workflow.pipeline import Pipeline


# --------------------------------------------------------------------------
# persistence: single reused client, non-blocking + coalesced, durable wait
# --------------------------------------------------------------------------


class _FakeQuery:
    def __init__(self, sink: list, table: str, op: str, payload) -> None:
        self._sink = sink
        self._table = table
        self._op = op
        self._payload = payload

    async def execute(self):
        self._sink.append((self._table, self._op, self._payload))
        return None


class _FakeTable:
    def __init__(self, sink: list, name: str) -> None:
        self._sink = sink
        self._name = name

    def upsert(self, payload, on_conflict=None):
        return _FakeQuery(self._sink, self._name, "upsert", payload)

    def insert(self, payload):
        return _FakeQuery(self._sink, self._name, "insert", payload)


class _FakeClient:
    instances = 0
    all_writes: list = []

    def __init__(self, settings, *, use_secret_key=False) -> None:
        self.writes = type(self).all_writes

    async def __aenter__(self):
        type(self).instances += 1
        return self

    async def __aexit__(self, *exc):
        return None

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self.writes, name)

    @classmethod
    def reset(cls) -> None:
        cls.instances = 0
        cls.all_writes = []


def _settings() -> SupabaseSettings:
    return SupabaseSettings(url="http://localhost", secret_key="secret")


def _state_and_ctx():
    pipeline = Pipeline(nodes=[])
    state = pipeline.create_query("A problem", "manual", "baseline")
    return state, pipeline.get_context(state.query_id)


def test_disabled_recorder_is_noop() -> None:
    recorder = StudySessionRecorder(
        SupabaseSettings(url=None, publishable_key=None, secret_key=None)
    )
    assert recorder.enabled is False
    state, ctx = _state_and_ctx()

    async def go():
        await recorder.upsert_session(
            state=state, ctx=ctx, backend_snapshot={}, wait=True
        )
        await recorder.aclose()

    asyncio.run(go())  # must not raise or touch the network


def test_wait_true_is_durable_and_reuses_one_client(monkeypatch) -> None:
    _FakeClient.reset()
    monkeypatch.setattr(study_mod, "SupabaseClient", _FakeClient)
    recorder = StudySessionRecorder(_settings())
    state, ctx = _state_and_ctx()

    async def go():
        for _ in range(3):
            await recorder.upsert_session(
                state=state, ctx=ctx, backend_snapshot={"n": 1}, wait=True
            )
        await recorder.aclose()

    asyncio.run(go())
    # Every wait=True call is durable before returning...
    assert len(_FakeClient.all_writes) == 3
    # ...and they all rode a single long-lived client, not one-per-call.
    assert _FakeClient.instances == 1


def test_non_blocking_upserts_coalesce_per_query(monkeypatch) -> None:
    _FakeClient.reset()
    monkeypatch.setattr(study_mod, "SupabaseClient", _FakeClient)
    recorder = StudySessionRecorder(_settings())
    state, ctx = _state_and_ctx()

    async def go():
        # Enqueue several snapshots without yielding to the worker between them:
        # they should collapse to the freshest write for this query_id.
        for i in range(5):
            await recorder.upsert_session(
                state=state, ctx=ctx, backend_snapshot={"n": i}
            )
        await recorder.aclose()

    asyncio.run(go())
    upserts = [w for w in _FakeClient.all_writes if w[1] == "upsert"]
    assert len(upserts) < 5  # coalesced
    assert upserts[-1][2]["backend_snapshot"] == {"n": 4}  # freshest wins


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
        response=AgentResponse(
            claim="c", rationale="r", message="m", evidence=["42"]
        ),
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
