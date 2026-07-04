import asyncio
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from mars.config.settings import OpenRouterSettings
from mars.llm.providers.base import (
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    ProviderType,
    StructuredResponse,
    TokenUsage,
)

T = TypeVar("T", bound=BaseModel)

STRUCTURED_RETRIES = 3
EMPTY_RESPONSE_RETRIES = 3
EMPTY_RESPONSE_BACKOFF = 1.5


def empty_detail(response: Any, choice: Any) -> str:
    error = getattr(response, "error", None) or getattr(choice, "error", None)
    if error is not None:
        return str(getattr(error, "message", None) or error)
    return f"finish_reason={getattr(choice, 'finish_reason', None)}"


def extract_usage(response: Any) -> TokenUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
    )


class OpenRouterProvider(LLMProvider):
    name = ProviderType.OPENROUTER

    def __init__(self, *, api_key: str, config: OpenRouterSettings) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            max_retries=config.retry_attempts,
        )
        self._config = config

    @classmethod
    def from_settings(cls, settings: OpenRouterSettings) -> "OpenRouterProvider":
        if settings.api_key is None:
            raise LLMProviderError("OpenRouterSettings.api_key is required")
        return cls(api_key=settings.api_key.get_secret_value(), config=settings)

    @property
    def client(self) -> AsyncOpenAI:
        return self._client

    def _kwargs(self, *, temperature: float | None) -> dict[str, Any]:
        cfg = self._config
        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "temperature": cfg.temperature if temperature is None else temperature,
        }
        if cfg.max_output_tokens is not None:
            kwargs["max_tokens"] = cfg.max_output_tokens
        return kwargs

    def _provider_routing(self, *, require_parameters: bool = False) -> dict[str, Any]:
        provider: dict[str, Any] = {"allow_fallbacks": True}
        if self._config.provider_sort:
            provider["sort"] = self._config.provider_sort
        if require_parameters:
            provider["require_parameters"] = True
        return {"provider": provider}

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        thinking_level: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        detail = "unknown"
        for attempt in range(EMPTY_RESPONSE_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    messages=messages,  # type: ignore[arg-type]
                    extra_body=self._provider_routing(),
                    **self._kwargs(temperature=temperature),
                )
            except Exception as exc:
                raise LLMProviderError(f"OpenRouter call failed: {exc}") from exc
            choice = response.choices[0]
            content = choice.message.content or ""
            if content:
                return LLMResponse(
                    content=content,
                    usage=extract_usage(response),
                    model=self._config.model,
                    provider=ProviderType.OPENROUTER,
                    finish_reason=choice.finish_reason,
                )
            detail = empty_detail(response, choice)
            if attempt < EMPTY_RESPONSE_RETRIES - 1:
                await asyncio.sleep(EMPTY_RESPONSE_BACKOFF * 2**attempt)
        raise LLMProviderError(
            f"OpenRouter returned an empty response after {EMPTY_RESPONSE_RETRIES} attempts ({detail})"
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
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": False,
                "schema": schema.model_json_schema(),
            },
        }
        last_error: Exception | None = None
        for _ in range(STRUCTURED_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    messages=messages,  # type: ignore[arg-type]
                    response_format=response_format,  # type: ignore[arg-type]
                    extra_body=self._provider_routing(require_parameters=True),
                    **self._kwargs(temperature=temperature),
                )
            except Exception as exc:
                raise LLMProviderError(f"OpenRouter structured call failed: {exc}") from exc
            choice = response.choices[0]
            content = choice.message.content or ""
            try:
                parsed = schema.model_validate_json(content)
            except ValidationError as exc:
                last_error = exc
                continue
            return StructuredResponse(
                parsed=parsed,
                usage=extract_usage(response),
                model=self._config.model,
                provider=ProviderType.OPENROUTER,
                finish_reason=choice.finish_reason,
            )
        raise LLMProviderError(
            f"OpenRouter structured validation failed after {STRUCTURED_RETRIES} attempts: {last_error}"
        )

    async def create_cache(
        self, *, system_instruction: str, content: str, ttl_seconds: int = 3600
    ) -> str:
        raise LLMProviderError("OpenRouterProvider does not support explicit caching")

    async def delete_cache(self, cache_name: str) -> None:
        return None
