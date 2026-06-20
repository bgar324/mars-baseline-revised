import hashlib
import json
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, directory: str | None) -> None:
        self.dir = Path(directory) if directory else None
        if self.dir is not None:
            self.dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self.dir is not None

    @staticmethod
    def key(
        method: str,
        path: str,
        params: dict[str, Any] | None,
        body: Any | None,
    ) -> str:
        raw = "|".join(
            [
                method,
                path,
                json.dumps(params or {}, sort_keys=True, default=str),
                json.dumps(body or {}, sort_keys=True, default=str),
            ]
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        if self.dir is None:
            return None
        path = self.dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None

    def set(self, key: str, value: Any) -> None:
        if self.dir is None:
            return
        try:
            (self.dir / f"{key}.json").write_text(json.dumps(value))
        except (OSError, TypeError):
            ...
