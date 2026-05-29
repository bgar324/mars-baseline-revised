from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, Protocol, TypeVar

import numpy as np
from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class ProviderType(str, Enum):
    GEMINI = "gemini"


class ProviderError(Exception):
    """Base error for provider failures."""


class LLMProviderError(ProviderError):
    """Raised when an LLM provider call fails."""


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0


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
    """Abstract base for conversational LLM providers."""

    name: ProviderType

    @abstractmethod
    async def generate(self, *, messages: list[dict[str, str]]) -> LLMResponse:
        """Generate a text response."""

    @abstractmethod
    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type[T],
        cache_name: str | None = None,
        temperature: float | None = None,
        thinking_disabled: bool = False,
    ) -> StructuredResponse[T]:
        """Generate a response and parse it into the given schema.

        ``temperature`` overrides the provider default for this one call.
        ``cache_name`` reuses a previously cached prompt prefix.
        ``thinking_disabled`` skips reasoning tokens for this call so the
        full output budget goes to the structured response.
        """

    @abstractmethod
    async def create_cache(
        self, *, system_instruction: str, content: str, ttl_seconds: int = 3600
    ) -> str:
        """Store a reusable prompt prefix and return a handle to it."""

    @abstractmethod
    async def delete_cache(self, cache_name: str) -> None:
        """Discard a stored prompt prefix."""


class EmbeddingProvider(Protocol):
    """Turns text into embedding vectors."""

    async def embed(self, text: str) -> np.ndarray: ...

    async def embed_batch(self, texts: list[str]) -> np.ndarray: ...
