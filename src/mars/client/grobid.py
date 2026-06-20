from typing import Any

from mars.client.base import BaseClient
from mars.client.tei import Parser
from mars.models.grobid import Article
from mars.schemas.grobid import Form, Response

_ERROR_CODES = {
    203: "Content couldn't be extracted",
    400: "Wrong request, missing parameters, missing header",
    500: "Internal service error",
    503: "Service not available",
}


class GrobidError(Exception): ...


class GrobidClient(BaseClient):
    async def parse_pdf(self, form: Form) -> Article:
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
        form = kwargs["form"]
        if not isinstance(form, Form):
            raise TypeError("fetch() requires a `form` of type Form")
        return await self.parse_pdf(form)
