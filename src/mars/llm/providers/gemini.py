import asyncio
import logging
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from mars.config.settings import GeminiSettings

logger = logging.getLogger(__name__)

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


class GoogleGeminiClient:
    """Async wrapper around the Google GenAI SDK."""

    def __init__(self, *, api_key: str, default_config: GeminiSettings) -> None:
        self._client = genai.Client(api_key=api_key)
        self._default_config = default_config

    @classmethod
    def from_settings(cls, settings: GeminiSettings) -> "GoogleGeminiClient":
        return cls(
            api_key=settings.api_key.get_secret_value(),
            default_config=settings,
        )

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        config: GeminiSettings | None = None,
    ) -> str:
        """Send messages to Gemini and return the generated text."""
        cfg = config or self._default_config
        system_instruction, contents = prepare_contents(messages)

        gen_config_kwargs: dict[str, Any] = dict(
            system_instruction=system_instruction,
            max_output_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            top_k=cfg.top_k,
        )
        thinking_config = build_thinking_config(cfg)
        if thinking_config is not None:
            gen_config_kwargs["thinking_config"] = thinking_config

        gen_config = types.GenerateContentConfig(**gen_config_kwargs)

        response = await self._client.aio.models.generate_content(
            model=cfg.model,
            contents=contents,  # type: ignore[arg-type]
            config=gen_config,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return response.text

    async def generate_completions(
        self,
        *,
        messages: list[dict[str, str]],
        n: int = 1,
        config: GeminiSettings | None = None,
    ) -> str | list[str]:
        """Generate one or more completions, firing n concurrent requests."""
        if n <= 1:
            return await self.generate(messages=messages, config=config)

        tasks = [self.generate(messages=messages, config=config) for _ in range(n)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        completions: list[str] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Gemini concurrent call failed: %s", result)
                continue
            completions.append(result)

        if not completions:
            raise RuntimeError("All Gemini concurrent generation calls failed")

        return completions

    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[T],
        config: GeminiSettings | None = None,
    ) -> T:
        """Send messages to Gemini and parse the response into a Pydantic model."""
        cfg = config or self._default_config
        system_instruction, contents = prepare_contents(messages)

        gen_config_kwargs: dict[str, Any] = dict(
            system_instruction=system_instruction,
            max_output_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            top_k=cfg.top_k,
            response_mime_type="application/json",
            response_schema=schema,
        )
        thinking_config = build_thinking_config(cfg)
        if thinking_config is not None:
            gen_config_kwargs["thinking_config"] = thinking_config

        gen_config = types.GenerateContentConfig(**gen_config_kwargs)

        response = await self._client.aio.models.generate_content(
            model=cfg.model,
            contents=contents,  # type: ignore[arg-type]
            config=gen_config,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return schema.model_validate_json(response.text)
