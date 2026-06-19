from enum import Enum

from pydantic import BaseModel, Field


class PageRange(BaseModel):
    from_page: int
    to_page: int


class Scope(BaseModel):
    volume: int | None = None
    pages: PageRange | None = None

    def is_empty(self) -> bool:
        return self.volume is None and self.pages is None


class Date(BaseModel):
    year: str
    month: str | None = None
    day: str | None = None


class PersonName(BaseModel):
    surname: str
    first_name: str | None = None

    def to_string(self) -> str:
        if self.first_name:
            return f"{self.first_name} {self.surname}"
        return self.surname


class Affiliation(BaseModel):
    department: str | None = None
    institution: str | None = None
    laboratory: str | None = None

    def is_empty(self) -> bool:
        return all(getattr(self, name) is None for name in type(self).model_fields)


class Author(BaseModel):
    person_name: PersonName
    affiliations: list[Affiliation] = Field(default_factory=list)
    email: str | None = None


class CitationIdentifiers(BaseModel):
    DOI: str | None = None
    arXiv: str | None = None

    def is_empty(self) -> bool:
        return self.DOI is None and self.arXiv is None


class Citation(BaseModel):
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
    bibr = "bibr"
    figure = "figure"
    table = "table"
    box = "box"
    formula = "formula"


class Ref(BaseModel):
    start: int
    end: int
    marker: Marker | None = None
    target: str | None = None


class RefText(BaseModel):
    text: str
    refs: list[Ref] = Field(default_factory=list)

    @property
    def plain_text(self) -> str:
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
    title: str
    paragraphs: list[RefText] = Field(default_factory=list)

    def to_str(self) -> str:
        text = ""
        for paragraph in self.paragraphs:
            text += paragraph.plain_text
        return text


class Table(BaseModel):
    heading: str
    description: str | None = None
    rows: list[list[str]] = Field(default_factory=list)


class Article(BaseModel):
    bibliography: Citation
    keywords: set[str]
    citations: dict[str, Citation]
    sections: list[Section]
    tables: dict[str, Table]
    abstract: Section | None = None
