from pydantic import BaseModel, Field


class Author(BaseModel):
    id: str | None = None
    name: str


class AuthorDetail(BaseModel):
    id: str
    name: str
    url: str | None = None
    affiliations: list[str] = Field(default_factory=list)
    homepage: str | None = None
    paper_count: int | None = None
    citation_count: int | None = None
    h_index: int | None = None


class FieldOfStudy(BaseModel):
    category: str
    source: str | None = None


class PublicationVenue(BaseModel):
    id: str | None = None
    name: str | None = None
    type: str | None = None
    alternate_names: list[str] = Field(default_factory=list)
    url: str | None = None


class Paper(BaseModel):
    id: str
    title: str
    corpus_id: int | None = None
    abstract: str | None = None
    tldr: str | None = None
    venue: str | None = None
    publication_venue: PublicationVenue | None = None
    publication_types: list[str] = Field(default_factory=list)
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
    s2_fields_of_study: list[FieldOfStudy] = Field(default_factory=list)
    text_availability: str | None = None
    authors: list[Author] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)
    specter_v2: list[float] | None = None


class CitationEdge(BaseModel):
    paper: Paper
    contexts: list[str] = Field(default_factory=list)
    intents: list[str] = Field(default_factory=list)
    is_influential: bool = False


class TextSpan(BaseModel):
    start: int
    end: int


class Snippet(BaseModel):
    text: str
    paper: Paper
    kind: str | None = None
    section: str | None = None
    offset: TextSpan | None = None
    score: float | None = None
