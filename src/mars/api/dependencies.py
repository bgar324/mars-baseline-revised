from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from mars.client.s2 import SemanticScholarClient
from mars.config.settings import AppSettings, DebateSettings
from mars.llm.providers.gemini import GeminiProvider
from mars.session_cache import SessionCache
from mars.workflow.pipeline import Pipeline, build

if TYPE_CHECKING:
    from mars.llm.providers.langextract import LangExtractProvider


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def get_gemini() -> GeminiProvider:
    return GeminiProvider.from_settings(get_settings().gemini)


@lru_cache(maxsize=1)
def get_s2() -> SemanticScholarClient:
    return SemanticScholarClient.from_env(get_settings().s2)


@lru_cache(maxsize=1)
def get_langextract() -> LangExtractProvider:
    from mars.llm.providers.langextract import LangExtractProvider

    return LangExtractProvider(get_settings().langextract)


@lru_cache(maxsize=1)
def get_judge_provider() -> GeminiProvider:
    return GeminiProvider.from_settings(
        DebateSettings(api_key=get_settings().gemini.api_key)
    )


@lru_cache(maxsize=1)
def get_session_cache() -> SessionCache:
    return SessionCache()


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    settings = get_settings()
    return build(
        langextract=get_langextract(),
        gemini=get_gemini(),
        s2=get_s2(),
        judge_llm=get_judge_provider(),
        retrieval_config=settings.pipeline.retrieval,
        cluster_config=settings.pipeline.clustering,
        retrieval_filters={
            "minCitationCount": settings.pipeline.retrieval.min_citation_count
        },
        include_debate=True,
        recorder=get_session_cache(),
    )
