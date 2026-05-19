from collections.abc import Mapping
from datetime import datetime
from typing import Any


class RecordMixin:
    """Map plain record data into domain models."""

    @staticmethod
    def _dt(record: Mapping[str, Any], key: str) -> datetime:
        value = record[key]
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise TypeError(
            f"Cannot parse datetime from {type(value).__name__} at key {key!r}."
        )

    @staticmethod
    def _dt_opt(record: Mapping[str, Any], key: str) -> datetime | None:
        value = record.get(key)
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise TypeError(
            f"Cannot parse datetime from {type(value).__name__} at key {key!r}."
        )
