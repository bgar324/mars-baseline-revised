from enum import Enum

from pydantic import BaseModel, Field


class PageRange(BaseModel):
    """Page boundaries from a biblScope element."""

    from_page: int
    to_page: int


class Scope(BaseModel):
    """Bibliographic scope from biblScope elements."""

    volume: int | None = None
    pages: PageRange | None = None

    def is_empty(self) -> bool:
        """Return whether no scope information is present."""
        return self.volume is None and self.pages is None


class Date(BaseModel):
    """Publication date from a 'when' attribute."""

    year: str
    month: str | None = None
    day: str | None = None


class PersonName(BaseModel):
    """Person name from a persName element."""

    surname: str
    first_name: str | None = None

    def to_string(self) -> str:
        """Return the name as readable text."""
        if self.first_name:
            return f"{self.first_name} {self.surname}"
        return self.surname


class Affiliation(BaseModel):
    """Author affiliation."""

    department: str | None = None
    institution: str | None = None
    laboratory: str | None = None

    def is_empty(self) -> bool:
        """Return whether no affiliation information is present."""
        return all(getattr(self, name) is None for name in type(self).model_fields)


class Author(BaseModel):
    """Author with affiliations."""

    person_name: PersonName
    affiliations: list[Affiliation] = Field(default_factory=list)
    email: str | None = None


class CitationIdentifiers(BaseModel):
    """External identifiers from idno elements."""

    DOI: str | None = None
    arXiv: str | None = None

    def is_empty(self) -> bool:
        """Return whether no identifier is present."""
        return self.DOI is None and self.arXiv is None


class Citation(BaseModel):
    """Bibliography entry from a biblStruct element."""

    title: str
    authors: list[Author] = Field(default_factory=list)
    date: Date | None = None
    ids: CitationIdentifiers | None = None
    target: str | None = None
    publisher: str | None = None
    journal: str | None = None
    series: str | None = None
    scope: Scope | None = None


class Marker(str, Enum):
    """Reference marker types."""

    bibr = "bibr"
    figure = "figure"
    table = "table"
    box = "box"
    formula = "formula"


class Ref(BaseModel):
    """Reference position within a paragraph."""

    start: int
    end: int
    marker: Marker | None = None
    target: str | None = None


class RefText(BaseModel):
    """Paragraph text with embedded references."""

    text: str
    refs: list[Ref] = Field(default_factory=list)

    @property
    def plain_text(self) -> str:
        """Return the paragraph text with reference spans removed."""
        if len(self.refs) == 0:
            return self.text

        ranges = [(ref.start, ref.end) for ref in self.refs]
        text = ""
        left_bound = 0
        for start, end in ranges:
            text += self.text[left_bound:start].rstrip()
            left_bound = end
        text += self.text[ranges[-1][1] :].rstrip()
        return text


class Section(BaseModel):
    """Document section with paragraphs."""

    title: str
    paragraphs: list[RefText] = Field(default_factory=list)

    def to_str(self) -> str:
        """Return the concatenated plain text of all paragraphs."""
        text = ""
        for paragraph in self.paragraphs:
            text += paragraph.plain_text
        return text


class Table(BaseModel):
    """Table from a figure element."""

    heading: str
    description: str | None = None
    rows: list[list[str]] = Field(default_factory=list)


class Article(BaseModel):
    """Parsed scholarly article."""

    bibliography: Citation
    keywords: set[str]
    citations: dict[str, Citation]
    sections: list[Section]
    tables: dict[str, Table]
    abstract: Section | None = None
