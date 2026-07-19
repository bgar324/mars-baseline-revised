import asyncio

from mars.llm.agents.persona import PersonaSpeaker, turn_log
from mars.llm.providers.base import LLMProvider
from mars.models.debate import (
    BaselineConversation,
    BaselineMessage,
    EvidenceSet,
)
from mars.schemas.debate import BaselineChatRequest
from mars.workflow.base import WorkflowContext


class BaselineChatError(Exception): ...


async def respond_to_researcher(
    ctx: WorkflowContext,
    request: BaselineChatRequest,
    provider: LLMProvider,
) -> BaselineConversation:
    if ctx.condition != "baseline":
        raise BaselineChatError("Interactive baseline chat is unavailable for this session.")
    if ctx.debate is None or ctx.cycle is None or ctx.cycle.status != "complete":
        raise BaselineChatError("Generate hypotheses before starting the discussion.")

    by_id = {str(agent.cluster_id): agent for agent in ctx.debate.agents}
    requested_ids = list(dict.fromkeys(request.agent_ids))
    if len(requested_ids) != 1:
        raise BaselineChatError("Choose one researcher for this discussion.")
    unknown = [agent_id for agent_id in requested_ids if agent_id not in by_id]
    if unknown:
        raise BaselineChatError("One or more selected researchers are unavailable.")

    agent_id = requested_ids[0]
    conversation = ctx.baseline_conversations.setdefault(agent_id, [])
    user_message = BaselineMessage(role="user", content=request.message.strip())

    if ctx.test_mode:
        await asyncio.sleep(8.0)
        agent = by_id[agent_id]
        evidence = ctx.cycle.evidence.get(agent_id, EvidenceSet())
        evidence_ids = [snippet.corpus_id for snippet in evidence.snippets[:2]]
        reply = BaselineMessage(
            role="agent",
            agent_id=agent_id,
            content=(
                f"From the {agent.reasoning_style} perspective, I would test "
                f"this by comparing delayed independent evaluation under two "
                f"workflow conditions. {agent.framing}"
            ),
            rationale=(
                "This simulated response connects the researcher's question "
                "to the persona's evaluation lens and available evidence."
            ),
            evidence=evidence_ids,
        )
        conversation.extend([user_message, reply])
        ctx.baseline_messages.extend([user_message, reply])
        return BaselineConversation(messages=conversation)

    speaker = PersonaSpeaker(provider=provider)
    async def answer(agent_id: str) -> BaselineMessage:
        agent_turns = [turn for turn in ctx.cycle.turns if turn.agent_id == agent_id]
        hypothesis = (
            agent_turns[-1].response.claim if agent_turns else ctx.cycle.focal_claim
        )
        return await speaker.respond_to_user(
            persona=by_id[agent_id],
            evidence=ctx.cycle.evidence.get(agent_id, EvidenceSet()),
            research_problem=ctx.raw_text,
            focal_claim=ctx.cycle.focal_claim,
            hypothesis=hypothesis,
            prior_turns=turn_log(agent_turns, {agent_id: by_id[agent_id].name}),
            history=ctx.baseline_messages,
            user_message=user_message.content,
        )

    reply = await answer(agent_id)
    conversation.extend([user_message, reply])
    ctx.baseline_messages.extend([user_message, reply])
    return BaselineConversation(messages=conversation)
