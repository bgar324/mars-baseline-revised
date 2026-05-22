from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from mars.config.settings import GeminiSettings
from mars.llm.providers.base import (
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    ProviderType,
    StructuredResponse,
    TokenUsage,
)


T = TypeVar("T", bound=BaseModel)


def build_thinking_config(cfg: GeminiSettings) -> types.ThinkingConfig | None:
    if not cfg.thinking_level:
        return None
    level = getattr(types.ThinkingLevel, cfg.thinking_level.upper())
    return types.ThinkingConfig(thinking_level=level)


def prepare_contents(
    messages: list[dict[str, str]],
) -> tuple[str | None, list[dict[str, Any]]]:
    system_instruction: str | None = None
    contents: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "user")
        text = msg.get("content", "")

        if role == "system":
            system_instruction = text
            continue

        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})

    return system_instruction, contents


def extract_usage(response: Any) -> TokenUsage:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        thinking_tokens=getattr(usage, "thoughts_token_count", 0) or 0,
        cached_tokens=getattr(usage, "cached_content_token_count", 0) or 0,
        total_tokens=getattr(usage, "total_token_count", 0) or 0,
    )


def extract_finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    reason = getattr(candidates[0], "finish_reason", None)
    return str(reason) if reason is not None else None


class GeminiProvider(LLMProvider):
    """Adapter for the Google GenAI SDK."""

    name = ProviderType.GEMINI

    def __init__(self, *, api_key: str, config: GeminiSettings) -> None:
        self._client = genai.Client(api_key=api_key)
        self._config = config

    @classmethod
    def from_settings(cls, settings: GeminiSettings) -> "GeminiProvider":
        return cls(
            api_key=settings.api_key.get_secret_value(),
            config=settings,
        )

    def _build_config(self, **extra: Any) -> types.GenerateContentConfig:
        cfg = self._config
        kwargs: dict[str, Any] = dict(
            max_output_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            top_k=cfg.top_k,
            **extra,
        )
        thinking_config = build_thinking_config(cfg)
        if thinking_config is not None:
            kwargs["thinking_config"] = thinking_config
        return types.GenerateContentConfig(**kwargs)

    async def _call(self, messages: list[dict[str, str]], **config_extra: Any) -> Any:
        system_instruction, contents = prepare_contents(messages)
        gen_config = self._build_config(
            system_instruction=system_instruction, **config_extra
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._config.model,
                contents=contents,  # type: ignore[arg-type]
                config=gen_config,
            )
        except Exception as exc:
            raise LLMProviderError(f"Gemini call failed: {exc}") from exc

        if not response.text:
            raise LLMProviderError("Gemini returned an empty response")
        return response

    async def generate(self, *, messages: list[dict[str, str]]) -> LLMResponse:
        response = await self._call(messages)
        return LLMResponse(
            content=response.text,
            usage=extract_usage(response),
            model=self._config.model,
            provider=ProviderType.GEMINI,
            finish_reason=extract_finish_reason(response),
        )

    async def generate_structured(
        self, *, messages: list[dict[str, str]], schema: type[T]
    ) -> StructuredResponse[T]:
        response = await self._call(
            messages,
            response_mime_type="application/json",
            response_schema=schema,
        )
        return StructuredResponse(
            parsed=schema.model_validate_json(response.text),
            usage=extract_usage(response),
            model=self._config.model,
            provider=ProviderType.GEMINI,
            finish_reason=extract_finish_reason(response),
        )
