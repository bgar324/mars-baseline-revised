from pydantic import field_validator

from mars.schemas.base import SchemaBase

Multipart = tuple[str | None, bytes, str | None]


class File(SchemaBase):
    """PDF file submitted to GROBID."""

    payload: bytes
    file_name: str | None = None
    mime_type: str | None = None

    def to_tuple(self) -> Multipart:
        """Return the httpx multipart tuple for this file."""
        return self.file_name, self.payload, self.mime_type


class Form(SchemaBase):
    """processFulltextDocument form data."""

    file: File
    segment_sentences: bool | None = None
    consolidate_header: int | None = None
    consolidate_citations: int | None = None
    include_raw_citations: bool | None = None
    include_raw_affiliations: bool | None = None
    tei_coordinates: str | None = None

    @field_validator("consolidate_header", "consolidate_citations")
    @classmethod
    def validate_consolidate_values(cls, v: int | None) -> int | None:
        """Validate consolidation levels are 0, 1, or 2."""
        if v is not None and v not in (0, 1, 2):
            raise ValueError("must be 0, 1, or 2")
        return v

    def to_files_and_data(
        self,
    ) -> tuple[dict[str, Multipart], dict[str, str]]:
        """Split the form into httpx files and data mappings."""
        files: dict[str, Multipart] = {"input": self.file.to_tuple()}
        data: dict[str, str] = {}

        if self.segment_sentences is not None:
            data["segmentSentences"] = "1" if self.segment_sentences else "0"

        if self.consolidate_header is not None:
            data["consolidateHeader"] = str(self.consolidate_header)

        if self.consolidate_citations is not None:
            data["consolidateCitations"] = str(self.consolidate_citations)

        if self.include_raw_citations is not None:
            data["includeRawCitations"] = "1" if self.include_raw_citations else "0"

        if self.include_raw_affiliations is not None:
            data["includeRawAffiliations"] = (
                "1" if self.include_raw_affiliations else "0"
            )

        if self.tei_coordinates is not None:
            data["teiCoordinates"] = self.tei_coordinates

        return files, data


class Response(SchemaBase):
    """GROBID API response."""

    status_code: int
    content: bytes
    content_type: str | None = None
