from enum import Enum
from pydantic import BaseModel, Field


class SemanticRole(str, Enum):
    DOMAIN = "domain"
    GOAL = "goal"
    CONSTRUCT = "construct"
    CLAIM = "claim"


class QuerySpan(BaseModel):
    id: str = Field(description="Unique identifier for this span.")
    text: str = Field(description="Exact substring of the query covered by this span.")
    char_span: tuple[int, int] = Field(
        description=(
            "Start and end character offsets of the span in raw_text, as "
            "[start, end) into the original string."
        )
    )
    role: SemanticRole = Field(
        description=(
            "Semantic role of the span. 'domain': scholarly field. 'goal': the "
            "intended outcome or research aim. 'construct': a variable, concept, or "
            "measure. 'claim': an asserted relationship to be tested."
        )
    )


class ExtractedQuery(BaseModel):
    raw_text: str = Field(description="The user's query verbatim.")
    spans: list[QuerySpan] = Field(
        description="Spans labeling the domain, goal, construct, and claim parts of raw_text."
    )
    claim: str = Field(description="The query restated as a single testable assertion.")


class ClaimUpdate(BaseModel):
    claim: str = Field(
        description="The revised claim restated as a single testable assertion."
    )


class ExpandedConstruct(BaseModel):
    construct_id: str = Field(description="id of the source construct QuerySpan.")
    construct_text: str = Field(
        description="text of the source construct, copied verbatim."
    )
    expansions: list[str] = Field(
        description=(
            "Alternative terms and phrasings for this construct used to query the "
            "literature, including synonyms, related measures, and standard "
            "terminology. Provide 5 to 8 entries."
        ),
        min_length=5,
        max_length=8,
    )


class QueryExpansion(BaseModel):
    domain: str = Field(
        description=(
            "The scholarly field the query operates in. Use the extracted domain "
            "span when present; otherwise infer it from the constructs."
        )
    )
    domain_inferred: bool = Field(
        description=(
            "true when domain was inferred from the constructs, false when copied "
            "from an extracted domain span."
        )
    )
    expansions: list[ExpandedConstruct] = Field(
        description="One ExpandedConstruct per construct span in the query."
    )


class HypotheticalQuestions(BaseModel):
    questions: list[str] = Field(
        description=(
            "Research questions phrased as paper titles or abstract sentences, "
            "built from the query's constructs and claim, used as retrieval "
            "anchors. Provide 6 to 8 entries."
        ),
        min_length=6,
        max_length=8,
    )


class RetrievalAnchors(BaseModel):
    hypothetical_queries: list[str] = Field(
        description="Hypothetical research questions used as retrieval anchors."
    )
    claim_query: str | None = Field(
        default=None,
        description="The claim phrased as a retrieval query, or null if unavailable.",
    )
