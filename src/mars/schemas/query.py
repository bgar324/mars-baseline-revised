from enum import Enum
from pydantic import BaseModel, Field


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
    claim: str


class ClaimUpdate(BaseModel):
    claim: str


class ExpandedConstruct(BaseModel):
    construct_id: str = Field(description="ID of the source QuerySpan")
    construct_text: str = Field(description="Original construct text")
    expansions: list[str] = Field(
        description="Semantically related terms for literature retrieval",
        min_length=5,
        max_length=8,
    )


class QueryExpansion(BaseModel):
    domain: str = Field(
        description="The scholarly field the query operates in, "
        "either taken from the extracted domain span or inferred "
        "from the constructs when no domain was extracted"
    )
    domain_inferred: bool = Field(
        description="True when domain was inferred by the model rather "
        "than taken from an extracted span"
    )
    expansions: list[ExpandedConstruct]


class HypotheticalQuestions(BaseModel):
    questions: list[str] = Field(
        description="Paper-title-style or abstract-style questions "
        "synthesized from the query's constructs and claim, used as "
        "additional retrieval anchors",
        min_length=3,
        max_length=5,
    )


class RetrievalAnchors(BaseModel):
    """Query strings used to retrieve candidate papers."""

    construct_queries: list[str] = Field(
        description="One query per construct, joining the construct with "
        "its expansions to widen recall"
    )
    hypothetical_queries: list[str]
    claim_query: str | None = None
