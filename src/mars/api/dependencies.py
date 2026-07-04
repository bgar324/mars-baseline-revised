from functools import lru_cache

from mars.client.s2 import SemanticScholarClient
from mars.config.settings import AppSettings, DebateSettings
from mars.db.study import StudySessionRecorder
from mars.llm.providers.gemini import GeminiProvider
from mars.llm.providers.langextract import LangExtractProvider
from mars.workflow.pipeline import Pipeline, build

SETTINGS = AppSettings()


def get_settings() -> AppSettings:
    return SETTINGS


@lru_cache(maxsize=1)
def get_gemini() -> GeminiProvider:
    return GeminiProvider.from_settings(SETTINGS.gemini)


@lru_cache(maxsize=1)
def get_s2() -> SemanticScholarClient:
    return SemanticScholarClient.from_env(SETTINGS.s2)


@lru_cache(maxsize=1)
def get_langextract() -> LangExtractProvider:
    return LangExtractProvider(SETTINGS.langextract)


@lru_cache(maxsize=1)
def get_judge_provider() -> GeminiProvider:
    return GeminiProvider.from_settings(DebateSettings(api_key=SETTINGS.gemini.api_key))


@lru_cache(maxsize=1)
def get_study_recorder() -> StudySessionRecorder:
    return StudySessionRecorder(SETTINGS.supabase)


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    return build(
        langextract=get_langextract(),
        gemini=get_gemini(),
        s2=get_s2(),
        judge_llm=get_judge_provider(),
        retrieval_config=SETTINGS.pipeline.retrieval,
        cluster_config=SETTINGS.pipeline.clustering,
        retrieval_filters={
            "minCitationCount": SETTINGS.pipeline.retrieval.min_citation_count
        },
        include_debate=True,
        recorder=get_study_recorder(),
    )
