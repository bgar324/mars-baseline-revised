import asyncio
import re
from typing import Any

import httpx

from mars.client.base import BaseClient
from mars.config.client import ClientConfig
from mars.config.settings import SemanticScholarSettings
from mars.models.s2 import (
    Author,
    AuthorDetail,
    CitationEdge,
    Paper,
    Snippet,
    TextSpan,
)

BASE_URL = "https://api.semanticscholar.org"

PAPER_FIELDS = (
    "paperId",
    "corpusId",
    "externalIds",
    "url",
    "title",
    "abstract",
    "venue",
    "year",
    "publicationDate",
    "referenceCount",
    "citationCount",
    "influentialCitationCount",
    "isOpenAccess",
    "openAccessPdf",
    "fieldsOfStudy",
    "authors",
    "embedding.specter_v2",
)

AUTHOR_FIELDS = (
    "authorId",
    "name",
    "url",
    "affiliations",
    "homepage",
    "paperCount",
    "citationCount",
    "hIndex",
)

SNIPPET_FIELDS = (
    "snippet.text",
    "snippet.snippetKind",
    "snippet.section",
    "snippet.snippetOffset",
)

_PAPER_FIELDS = ",".join(PAPER_FIELDS)
_AUTHOR_FIELDS = ",".join(AUTHOR_FIELDS)
_SNIPPET_FIELDS = ",".join(SNIPPET_FIELDS)

PREFIX = {
    "doi": "DOI",
    "arxiv": "ARXIV",
    "pmid": "PMID",
    "pmcid": "PMCID",
    "mag": "MAG",
    "acl": "ACL",
    "corpusid": "CorpusId",
    "url": "URL",
}

_URL_SITES = (
    "semanticscholar.org",
    "arxiv.org",
    "aclweb.org",
    "acm.org",
    "biorxiv.org",
)

_MAX_RETRIES = 3
_PAGE_LIMIT = 1000
_SEARCH_LIMIT = 100
_BATCH_LIMIT = 500

UNAUTHENTICATED_INTERVAL = 1.0


class SemanticScholarError(Exception):
    """Raised when the Semantic Scholar API fails or rejects a request."""


class SemanticScholarClient(BaseClient):
    """Async client for the Semantic Scholar Academic Graph API."""

    def __init__(self, config: ClientConfig) -> None:
        super().__init__(config)
        if config.api_key is None:
            self._rate_limiter.min_interval = max(
                self._rate_limiter.min_interval, UNAUTHENTICATED_INTERVAL
            )

    @classmethod
    def from_env(
        cls, settings: SemanticScholarSettings | None = None
    ) -> "SemanticScholarClient":
        """Build a client from SEMANTIC_SCHOLAR_API_KEY and .env settings."""
        settings = settings or SemanticScholarSettings()
        return cls(
            ClientConfig(
                base_url=settings.base_url,
                api_key=settings.api_key,
                request_timeout=settings.request_timeout,
                min_request_interval=settings.min_request_interval,
            )
        )

    def auth_headers(self) -> dict[str, str]:
        """Add the x-api-key header when an API key is configured."""
        if self.config.api_key is not None:
            return {"x-api-key": self.config.api_key.get_secret_value()}
        return {}

    @staticmethod
    def _normalize_id(identifier: str) -> str:
        """Map a paper identifier to a Semantic Scholar-supported form."""
        s = identifier.strip()
        low = s.lower()

        prefix = low.split(":", 1)[0]
        if prefix in PREFIX and ":" in s:
            _, _, rest = s.partition(":")
            return f"{PREFIX[prefix]}:{rest}"

        if re.fullmatch(r"[0-9a-f]{40}", s, re.IGNORECASE):
            return s
        if s.startswith("10."):
            return f"DOI:{s}"
        if "doi.org/" in low:
            return f"DOI:{s.split('doi.org/')[-1]}"
        if "arxiv.org/" in low:
            return f"ARXIV:{s.rstrip('/').split('/')[-1]}"
        if "semanticscholar.org/paper/" in low:
            return s.split("/paper/")[-1].split("?")[0]
        if low.startswith("http") and any(site in low for site in _URL_SITES):
            return f"URL:{s}"
        if s.isdigit():
            return f"CorpusId:{s}"
        return s

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any | None:
        """Send a request with rate limiting and retry on 429/5xx."""
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )
        backoff = 0.5
        for attempt in range(_MAX_RETRIES):
            await self._rate_limiter.wait()
            try:
                response = await self.session.request(
                    method, path, params=clean_params, json=json
                )
            except httpx.HTTPError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise SemanticScholarError(
                        f"Request to {path} failed: {exc}"
                    ) from exc
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code == 404:
                return None
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == _MAX_RETRIES - 1:
                    raise SemanticScholarError(
                        f"{response.status_code} from {path} after retries"
                    )
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise SemanticScholarError(
                    f"{response.status_code} from {path}: {response.text}"
                ) from exc
            return response.json()
        return None

    @staticmethod
    def _parse_paper(data: dict[str, Any]) -> Paper:
        ext = data.get("externalIds") or {}
        open_access = data.get("openAccessPdf") or {}
        authors: list[Author] = []
        for a in data.get("authors") or []:
            if isinstance(a, dict):
                name = a.get("name")
                if name:
                    authors.append(Author(id=a.get("authorId"), name=name))
            elif isinstance(a, str) and a:
                authors.append(Author(id=None, name=a))
        embedding = data.get("embedding") or {}
        specter_v2 = (
            embedding.get("vector")
            if embedding.get("model") == "specter_v2"
            else None
        )
        return Paper(
            id=data.get("paperId") or "",
            title=data.get("title") or "",
            corpus_id=data.get("corpusId"),
            abstract=data.get("abstract"),
            venue=data.get("venue"),
            year=data.get("year"),
            publication_date=data.get("publicationDate"),
            url=data.get("url"),
            doi=ext.get("DOI"),
            arxiv_id=ext.get("ARXIV"),
            citation_count=data.get("citationCount"),
            reference_count=data.get("referenceCount"),
            influential_citation_count=data.get("influentialCitationCount"),
            is_open_access=data.get("isOpenAccess"),
            open_access_pdf_url=open_access.get("url"),
            fields_of_study=data.get("fieldsOfStudy") or [],
            authors=authors,
            external_ids={k: str(v) for k, v in ext.items() if v is not None},
            specter_v2=specter_v2,
        )

    @staticmethod
    def _parse_author_detail(data: dict[str, Any]) -> AuthorDetail:
        return AuthorDetail(
            id=data.get("authorId") or "",
            name=data.get("name") or "",
            url=data.get("url"),
            affiliations=data.get("affiliations") or [],
            homepage=data.get("homepage"),
            paper_count=data.get("paperCount"),
            citation_count=data.get("citationCount"),
            h_index=data.get("hIndex"),
        )

    def _parse_edge(self, item: dict[str, Any], key: str) -> CitationEdge:
        return CitationEdge(
            paper=self._parse_paper(item.get(key) or {}),
            contexts=[str(c) for c in item.get("contexts") or []],
            intents=[str(i) for i in item.get("intents") or []],
            is_influential=bool(item.get("isInfluential")),
        )

    def _parse_snippet(self, item: dict[str, Any]) -> Snippet:
        snippet = item.get("snippet") or {}
        offsets = snippet.get("snippetOffset") or {}
        span = (
            TextSpan(start=offsets["start"], end=offsets["end"])
            if "start" in offsets and "end" in offsets
            else None
        )
        return Snippet(
            text=snippet.get("text") or "",
            paper=self._parse_paper(item.get("paper") or {}),
            kind=snippet.get("snippetKind"),
            section=snippet.get("section"),
            offset=span,
            score=item.get("score"),
        )

    async def get_paper(self, identifier: str) -> Paper | None:
        """Fetch a single paper by any supported identifier."""
        paper_id = self._normalize_id(identifier)
        data = await self._request(
            "GET", f"/graph/v1/paper/{paper_id}", params={"fields": _PAPER_FIELDS}
        )
        return self._parse_paper(data) if data else None

    async def search(
        self, query: str, *, limit: int = 10, offset: int = 0, **filters: Any
    ) -> list[Paper]:
        """Relevance-ranked paper search."""
        params = {
            "query": query,
            "limit": min(limit, _SEARCH_LIMIT),
            "offset": offset,
            "fields": _PAPER_FIELDS,
            **filters,
        }
        data = await self._request("GET", "/graph/v1/paper/search", params=params)
        return [self._parse_paper(p) for p in (data or {}).get("data", [])]

    async def match(self, title: str, **filters: Any) -> Paper | None:
        """Return the single closest paper by title, if any."""
        params = {"query": title, "fields": _PAPER_FIELDS, **filters}
        data = await self._request("GET", "/graph/v1/paper/search/match", params=params)
        if not data:
            return None
        items = data.get("data") or []
        return self._parse_paper(items[0]) if items else None

    async def get_citations(
        self, identifier: str, *, limit: int = _PAGE_LIMIT
    ) -> list[CitationEdge]:
        """Fetch papers that cite the given paper."""
        paper_id = self._normalize_id(identifier)
        return await self._collect_edges(
            f"/graph/v1/paper/{paper_id}/citations", "citingPaper", limit
        )

    async def get_references(
        self, identifier: str, *, limit: int = _PAGE_LIMIT
    ) -> list[CitationEdge]:
        """Fetch papers cited by the given paper."""
        paper_id = self._normalize_id(identifier)
        return await self._collect_edges(
            f"/graph/v1/paper/{paper_id}/references", "citedPaper", limit
        )

    async def _collect_edges(
        self, path: str, key: str, limit: int
    ) -> list[CitationEdge]:
        fields = "contexts,intents,isInfluential," + ",".join(
            f"{key}.{f}" for f in PAPER_FIELDS
        )
        edges: list[CitationEdge] = []
        offset = 0
        while len(edges) < limit:
            page = min(_PAGE_LIMIT, limit - len(edges))
            data = await self._request(
                "GET",
                path,
                params={"fields": fields, "limit": page, "offset": offset},
            )
            payload = data or {}
            items = payload.get("data") or []
            if not items:
                break
            edges.extend(self._parse_edge(it, key) for it in items)
            next_offset = payload.get("next")
            if next_offset is None or len(items) < page:
                break
            offset = (
                next_offset if isinstance(next_offset, int) else offset + len(items)
            )
        return edges[:limit]

    async def batch_papers(self, ids: list[str]) -> list[Paper]:
        """Fetch details for many papers at once (chunked at 500 ids)."""
        papers: list[Paper] = []
        for start in range(0, len(ids), _BATCH_LIMIT):
            chunk = [self._normalize_id(i) for i in ids[start : start + _BATCH_LIMIT]]
            data = await self._request(
                "POST",
                "/graph/v1/paper/batch",
                params={"fields": _PAPER_FIELDS},
                json={"ids": chunk},
            )
            papers.extend(self._parse_paper(p) for p in data or [] if p)
        return papers

    async def search_snippets(
        self, query: str, *, limit: int = 10, **filters: Any
    ) -> list[Snippet]:
        """Passage-level text search across the corpus."""
        params = {
            "query": query,
            "limit": min(limit, _PAGE_LIMIT),
            "fields": _SNIPPET_FIELDS,
            **filters,
        }
        data = await self._request("GET", "/graph/v1/snippet/search", params=params)
        return [self._parse_snippet(it) for it in (data or {}).get("data", [])]

    async def search_authors(
        self, query: str, *, limit: int = 10, offset: int = 0
    ) -> list[AuthorDetail]:
        """Search for authors by name."""
        params = {
            "query": query,
            "limit": min(limit, _SEARCH_LIMIT),
            "offset": offset,
            "fields": _AUTHOR_FIELDS,
        }
        data = await self._request("GET", "/graph/v1/author/search", params=params)
        return [self._parse_author_detail(a) for a in (data or {}).get("data", [])]

    async def get_author(self, author_id: str) -> AuthorDetail | None:
        """Fetch a single author profile."""
        data = await self._request(
            "GET",
            f"/graph/v1/author/{author_id}",
            params={"fields": _AUTHOR_FIELDS},
        )
        return self._parse_author_detail(data) if data else None

    async def get_author_papers(
        self, author_id: str, *, limit: int = _PAGE_LIMIT
    ) -> list[Paper]:
        """Fetch all papers by a given author."""
        papers: list[Paper] = []
        offset = 0
        while len(papers) < limit:
            page = min(_PAGE_LIMIT, limit - len(papers))
            data = await self._request(
                "GET",
                f"/graph/v1/author/{author_id}/papers",
                params={
                    "fields": _PAPER_FIELDS,
                    "limit": page,
                    "offset": offset,
                },
            )
            payload = data or {}
            items = payload.get("data") or []
            if not items:
                break
            papers.extend(self._parse_paper(p) for p in items)
            next_offset = payload.get("next")
            if next_offset is None or len(items) < page:
                break
            offset = (
                next_offset if isinstance(next_offset, int) else offset + len(items)
            )
        return papers[:limit]

    async def fetch(self, **kwargs: Any) -> list[Paper]:
        """Run a paper search. Expects a `query` keyword argument."""
        query = kwargs.get("query")
        if not isinstance(query, str):
            raise TypeError("fetch() requires a `query` keyword argument")
        return await self.search(query, limit=kwargs.get("limit", 10))
