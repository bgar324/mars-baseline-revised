from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from mars.config.settings import OpenAISettings
from mars.llm.providers.base import (
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    ProviderType,
    StructuredResponse,
    TokenUsage,
)


T = TypeVar("T", bound=BaseModel)


def extract_usage(response: Any) -> TokenUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
    )


class OpenAIProvider(LLMProvider):
    name = ProviderType.OPENAI

    def __init__(self, *, api_key: str, config: OpenAISettings) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            max_retries=config.retry_attempts,
        )
        self._config = config

    @classmethod
    def from_settings(cls, settings: OpenAISettings) -> "OpenAIProvider":
        if settings.api_key is None:
            raise LLMProviderError("OpenAISettings.api_key is required")
        return cls(api_key=settings.api_key.get_secret_value(), config=settings)

    def _kwargs(self, *, temperature: float | None) -> dict[str, Any]:
        cfg = self._config
        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "temperature": cfg.temperature if temperature is None else temperature,
        }
        if cfg.max_output_tokens is not None:
            kwargs["max_tokens"] = cfg.max_output_tokens
        return kwargs

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        thinking_level: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        try:
            response = await self._client.chat.completions.create(
                messages=messages,  # type: ignore[arg-type]
                **self._kwargs(temperature=temperature),
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI call failed: {exc}") from exc
        choice = response.choices[0]
        content = choice.message.content or ""
        if not content:
            raise LLMProviderError("OpenAI returned an empty response")
        return LLMResponse(
            content=content,
            usage=extract_usage(response),
            model=self._config.model,
            provider=ProviderType.OPENAI,
            finish_reason=choice.finish_reason,
        )

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
        try:
            response = await self._client.beta.chat.completions.parse(
                messages=messages,  # type: ignore[arg-type]
                response_format=schema,
                **self._kwargs(temperature=temperature),
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI structured call failed: {exc}") from exc
        choice = response.choices[0]
        parsed = choice.message.parsed
        if parsed is None:
            raise LLMProviderError("OpenAI returned no parsed content")
        return StructuredResponse(
            parsed=parsed,
            usage=extract_usage(response),
            model=self._config.model,
            provider=ProviderType.OPENAI,
            finish_reason=choice.finish_reason,
        )

    async def create_cache(
        self, *, system_instruction: str, content: str, ttl_seconds: int = 3600
    ) -> str:
        raise LLMProviderError("OpenAIProvider does not support explicit caching")

    async def delete_cache(self, cache_name: str) -> None:
        return None
