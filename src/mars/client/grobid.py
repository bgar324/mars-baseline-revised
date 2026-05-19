"""GROBID HTTP client: PDF bytes to a parsed Article."""

from typing import Any

from mars.client.base import BaseClient
from mars.client.tei import Parser
from mars.models.grobid import Article
from mars.schemas.grobid import Form, Response

# GROBID-specific status codes mapped to readable causes.
_ERROR_CODES = {
    203: "Content couldn't be extracted",
    400: "Wrong request, missing parameters, missing header",
    500: "Internal service error",
    503: "Service not available",
}


class GrobidError(Exception):
    """Raised when GROBID rejects a request or fails to process it."""


class GrobidClient(BaseClient):
    """Submit PDFs to GROBID and parse the TEI response."""

    async def parse_pdf(self, form: Form) -> Article:
        """Process a PDF through GROBID and return the parsed Article.

        Raises:
            GrobidError: If GROBID returns a known error status code.
            ParserError: If the returned TEI document is malformed.
        """
        await self._rate_limiter.wait()

        files, data = form.to_files_and_data()
        http_response = await self.session.post(
            "/api/processFulltextDocument",
            files=files,
            data=data,
        )

        response = Response(
            status_code=http_response.status_code,
            content=http_response.content,
            content_type=http_response.headers.get("content-type"),
        )

        if (cause := _ERROR_CODES.get(response.status_code)) is not None:
            raise GrobidError(f"{response.status_code}: {cause}")

        return Parser(response.content).parse()

    async def fetch(self, **kwargs: Any) -> Article:
        """Process a PDF through GROBID. Expects a `form` keyword argument."""
        form = kwargs["form"]
        if not isinstance(form, Form):
            raise TypeError("fetch() requires a `form` of type Form")
        return await self.parse_pdf(form)
