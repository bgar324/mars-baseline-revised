from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, TypeVar

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
        self, *, messages: list[dict[str, str]], schema: type[T]
    ) -> StructuredResponse[T]:
        """Generate a response parsed into the given Pydantic schema."""
