from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from mars.llm.providers.base import (
    LLMProvider,
    LLMResponse,
    StructuredResponse,
    T,
    TokenUsage,
)


@dataclass(slots=True)
class CallRecord:
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str | None = None
    model: str | None = None


active_call: ContextVar[CallRecord | None] = ContextVar("active_call", default=None)


def record(*, usage: TokenUsage, provider: str, model: str) -> None:
    rec = active_call.get()
    if rec is None:
        return
    rec.usage.input_tokens += usage.input_tokens
    rec.usage.output_tokens += usage.output_tokens
    rec.usage.thinking_tokens += usage.thinking_tokens
    rec.usage.cached_tokens += usage.cached_tokens
    rec.usage.total_tokens += usage.total_tokens
    rec.provider = provider
    rec.model = model


def note_model(provider: str, model: str) -> None:
    rec = active_call.get()
    if rec is not None:
        rec.provider = provider
        rec.model = model


def begin_step() -> Token:
    return active_call.set(CallRecord())


def end_step(token: Token) -> CallRecord:
    rec = active_call.get() or CallRecord()
    active_call.reset(token)
    return rec


class UsageTracker(LLMProvider):
    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.name = inner.name

    async def generate(
        self, *, messages: list[dict[str, str]], thinking_level: str | None = None
    ) -> LLMResponse:
        r = await self._inner.generate(messages=messages, thinking_level=thinking_level)
        record(usage=r.usage, provider=r.provider.value, model=r.model)
        return r

    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[T],
        cache_name: str | None = None,
        temperature: float | None = None,
        thinking_disabled: bool = False,
        thinking_level: str | None = None,
    ) -> StructuredResponse[T]:
        r = await self._inner.generate_structured(
            messages=messages,
            schema=schema,
            cache_name=cache_name,
            temperature=temperature,
            thinking_disabled=thinking_disabled,
            thinking_level=thinking_level,
        )
        record(usage=r.usage, provider=r.provider.value, model=r.model)
        return r

    async def create_cache(
        self, *, system_instruction: str, content: str, ttl_seconds: int = 3600
    ) -> str:
        return await self._inner.create_cache(
            system_instruction=system_instruction,
            content=content,
            ttl_seconds=ttl_seconds,
        )

    async def delete_cache(self, cache_name: str) -> None:
        return await self._inner.delete_cache(cache_name)
