import asyncio

from mars.llm.agents.persona import PersonaSpeaker
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
    if ctx.debate is None or ctx.cycle is None or ctx.cycle.synthesis is None:
        raise BaselineChatError("Generate hypotheses before starting the discussion.")

    by_id = {str(agent.cluster_id): agent for agent in ctx.debate.agents}
    requested_ids = list(dict.fromkeys(request.agent_ids))
    unknown = [agent_id for agent_id in requested_ids if agent_id not in by_id]
    if unknown:
        raise BaselineChatError("One or more selected researchers are unavailable.")

    user_message = BaselineMessage(role="user", content=request.message.strip())

    if ctx.test_mode:
        await asyncio.sleep(8.0)
        replies = []
        for agent_id in requested_ids:
            agent = by_id[agent_id]
            evidence = ctx.cycle.evidence.get(agent_id, EvidenceSet())
            evidence_ids = [snippet.corpus_id for snippet in evidence.snippets[:2]]
            replies.append(
                BaselineMessage(
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
            )
        ctx.baseline_messages.extend([user_message, *replies])
        return BaselineConversation(messages=ctx.baseline_messages)

    speaker = PersonaSpeaker(provider=provider)
    meta_review = ctx.cycle.synthesis.meta_review

    async def answer(agent_id: str) -> BaselineMessage:
        return await speaker.respond_to_user(
            persona=by_id[agent_id],
            evidence=ctx.cycle.evidence.get(agent_id, EvidenceSet()),
            research_problem=ctx.raw_text,
            focal_claim=ctx.cycle.focal_claim,
            meta_review=meta_review,
            history=ctx.baseline_messages,
            user_message=user_message.content,
        )

    replies = await asyncio.gather(*(answer(agent_id) for agent_id in requested_ids))
    ctx.baseline_messages.extend([user_message, *replies])
    return BaselineConversation(messages=ctx.baseline_messages)
