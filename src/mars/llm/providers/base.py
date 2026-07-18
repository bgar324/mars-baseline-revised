from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    import numpy as np


T = TypeVar("T", bound=BaseModel)


class ProviderType(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class ProviderError(Exception): ...


class LLMProviderError(ProviderError): ...


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0

    def __str__(self) -> str:
        return f"in={self.input_tokens} out={self.output_tokens} cached={self.cached_tokens}"


class LLMResponse(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    provider: ProviderType
    finish_reason: str | None = None


class StructuredResponse(BaseModel, Generic[T]):
    parsed: T
    usage: TokenUsage
    model: str
    provider: ProviderType
    finish_reason: str | None = None


class LLMProvider(ABC):
    name: ProviderType

    @abstractmethod
    async def generate(
        self, *, messages: list[dict[str, str]], thinking_level: str | None = None
    ) -> LLMResponse: ...

    @abstractmethod
    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[T],
        cache_name: str | None = None,
        temperature: float | None = None,
        thinking_disabled: bool = False,
        thinking_level: str | None = None,
    ) -> StructuredResponse[T]: ...

    @abstractmethod
    async def create_cache(
        self, *, system_instruction: str, content: str, ttl_seconds: int = 3600
    ) -> str: ...

    @abstractmethod
    async def delete_cache(self, cache_name: str) -> None: ...


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> np.ndarray: ...

    async def embed_batch(self, texts: list[str]) -> np.ndarray: ...
