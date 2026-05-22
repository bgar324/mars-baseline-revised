from functools import lru_cache

from mars.client.s2 import SemanticScholarClient
from mars.config.settings import AppSettings
from mars.llm.providers.gemini import GeminiProvider
from mars.llm.providers.langextract import LangExtractProvider
from mars.services.cluster import ClusterService
from mars.services.persona import PersonaService
from mars.services.pipeline import PipelineService
from mars.services.query import QueryService
from mars.services.retrieval import RetrievalService


_settings = AppSettings()


def get_settings() -> AppSettings:
    return _settings


@lru_cache(maxsize=1)
def get_gemini() -> GeminiProvider:
    return GeminiProvider.from_settings(_settings.gemini)


@lru_cache(maxsize=1)
def get_s2() -> SemanticScholarClient:
    return SemanticScholarClient.from_env(_settings.s2)


@lru_cache(maxsize=1)
def get_langextract() -> LangExtractProvider:
    return LangExtractProvider(_settings.langextract)


def get_query_service() -> QueryService:
    return QueryService(langextract=get_langextract(), gemini=get_gemini())


def get_retrieval_service() -> RetrievalService:
    return RetrievalService(s2=get_s2(), config=_settings.pipeline.retrieval)


def get_cluster_service() -> ClusterService:
    return ClusterService(config=_settings.pipeline.clustering)


def get_persona_service() -> PersonaService:
    return PersonaService(gemini=get_gemini())


@lru_cache(maxsize=1)
def get_pipeline() -> PipelineService:
    return PipelineService(
        query=get_query_service(),
        retrieval=get_retrieval_service(),
        cluster=get_cluster_service(),
        persona=get_persona_service(),
    )
