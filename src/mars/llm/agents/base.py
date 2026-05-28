from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from mars.llm.providers.base import LLMProvider, StructuredResponse


ResponseT = TypeVar("ResponseT", bound=BaseModel)


class AgentError(Exception):
    """Raised when an agent fails to produce a valid response."""


class BaseAgent(BaseModel, Generic[ResponseT]):
    """Shared base for MARS agents."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    role: str
    provider: LLMProvider
    system_instruction: str
    max_retries: int = Field(default=3, ge=1)

    def build_input(self, context: dict[str, Any]) -> str:
        """Compose the user-message content for a single agent invocation."""
        raise NotImplementedError("Subclasses must implement build_input.")

    def response_schema(self) -> type[ResponseT]:
        """Return the Pydantic schema used to validate the provider response."""
        raise NotImplementedError("Subclasses must implement response_schema.")

    async def run(self, context: dict[str, Any]) -> ResponseT:
        """Execute one agent invocation against the configured provider."""
        raise NotImplementedError("Subclasses must implement run.")

    async def _generate(self, prompt: str) -> StructuredResponse[ResponseT]:
        return await self.provider.generate_structured(
            messages=[
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt},
            ],
            schema=self.response_schema(),
        )

    async def _with_retries(self, call: Callable[[], Awaitable[Any]]) -> Any:
        last_error: Exception | None = None
        for _ in range(self.max_retries):
            try:
                return await call()
            except Exception as exc:
                last_error = exc
        raise AgentError(
            f"{self.name} failed after {self.max_retries} attempts: {last_error}"
        ) from last_error
