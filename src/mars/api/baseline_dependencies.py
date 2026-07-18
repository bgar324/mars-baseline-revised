import os
from functools import lru_cache

from mars.client.s2 import SemanticScholarClient
from mars.config.settings import BaselineAppSettings, DebateSettings
from mars.llm.providers.gemini import GeminiProvider
from mars.session_cache import SessionCache
from mars.workflow.pipeline import Pipeline, build_baseline

SETTINGS = BaselineAppSettings()


@lru_cache(maxsize=1)
def get_baseline_gemini() -> GeminiProvider:
    return GeminiProvider.from_settings(SETTINGS.gemini)


@lru_cache(maxsize=1)
def get_baseline_s2() -> SemanticScholarClient:
    settings = SETTINGS.s2
    if os.environ.get("VERCEL"):
        settings = settings.model_copy(update={"cache_dir": "/tmp/mars-s2-cache"})
    return SemanticScholarClient.from_env(settings)


@lru_cache(maxsize=1)
def get_baseline_judge() -> GeminiProvider:
    return GeminiProvider.from_settings(DebateSettings(api_key=SETTINGS.gemini.api_key))


@lru_cache(maxsize=1)
def get_baseline_session_cache() -> SessionCache:
    return SessionCache()


@lru_cache(maxsize=1)
def get_baseline_pipeline() -> Pipeline:
    return build_baseline(
        gemini=get_baseline_gemini(),
        s2=get_baseline_s2(),
        judge_llm=get_baseline_judge(),
        retrieval_filters={
            "minCitationCount": SETTINGS.pipeline.retrieval.min_citation_count
        },
        recorder=get_baseline_session_cache(),
    )


async def get_restored_baseline_pipeline(query_id: str | None = None) -> Pipeline:
    pipeline = get_baseline_pipeline()
    if query_id:
        snapshot = await get_baseline_session_cache().load_session(query_id)
        if snapshot is not None:
            pipeline.restore_session(snapshot)
    return pipeline
