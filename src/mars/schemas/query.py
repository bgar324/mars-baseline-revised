from enum import Enum
from pydantic import BaseModel


class SemanticRole(str, Enum):
    DOMAIN = "domain"
    GOAL = "goal"
    CONSTRUCT = "construct"
    CLAIM = "claim"


class QuerySpan(BaseModel):
    id: str
    text: str
    char_span: tuple[int, int]
    role: SemanticRole


class ExtractedQuery(BaseModel):
    raw_text: str
    spans: list[QuerySpan]
