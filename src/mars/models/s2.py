from pydantic import BaseModel, Field


class Author(BaseModel):
    """Author as embedded in a paper record."""

    id: str | None = None
    name: str


class AuthorDetail(BaseModel):
    """Full author profile from the author endpoints."""

    id: str
    name: str
    url: str | None = None
    affiliations: list[str] = Field(default_factory=list)
    homepage: str | None = None
    paper_count: int | None = None
    citation_count: int | None = None
    h_index: int | None = None


class Paper(BaseModel):
    """Scholarly paper."""

    id: str
    title: str
    corpus_id: int | None = None
    abstract: str | None = None
    venue: str | None = None
    year: int | None = None
    publication_date: str | None = None
    url: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    citation_count: int | None = None
    reference_count: int | None = None
    influential_citation_count: int | None = None
    is_open_access: bool | None = None
    open_access_pdf_url: str | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    authors: list[Author] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)


class CitationEdge(BaseModel):
    """A citation or reference link to a related paper."""

    paper: Paper
    contexts: list[str] = Field(default_factory=list)
    intents: list[str] = Field(default_factory=list)
    is_influential: bool = False


class TextSpan(BaseModel):
    """Character offset range within a source text."""

    start: int
    end: int


class Snippet(BaseModel):
    """A text passage extracted from a paper."""

    text: str
    paper: Paper
    kind: str | None = None
    section: str | None = None
    offset: TextSpan | None = None
    score: float | None = None
