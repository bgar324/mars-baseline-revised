import time
from dataclasses import dataclass

from mars.llm.providers.base import TokenUsage


def log(level: str, stage: str, event: str, fn: str, message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {level} — [STAGE: {stage}] [{event}] {fn}: {message}", flush=True)


@dataclass
class RunUsage:
    input: int = 0
    output: int = 0
    cached: int = 0

    def __iadd__(self, usage: TokenUsage) -> "RunUsage":
        self.input += usage.input_tokens
        self.output += usage.output_tokens
        self.cached += usage.cached_tokens
        return self

    def snapshot(self) -> tuple[int, int, int]:
        return (self.input, self.output, self.cached)

    def since(self, snap: tuple[int, int, int]) -> str:
        return (
            f"in={self.input - snap[0]} out={self.output - snap[1]} "
            f"cached={self.cached - snap[2]}"
        )

    def __str__(self) -> str:
        return f"in={self.input} out={self.output} cached={self.cached}"
