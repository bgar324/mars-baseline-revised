from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mars.api.baseline_dependencies import (
    get_baseline_gemini,
    get_baseline_recorder,
    get_baseline_s2,
    get_restored_baseline_pipeline,
)
from mars.api.dependencies import get_gemini, get_pipeline, get_s2
from mars.api.router import query_router
from mars.logging import configure_logging

# Vercel functions do not expose the multiprocessing semaphore used by
# Loguru's queued handlers.
configure_logging(enqueue=False)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await get_baseline_recorder().aclose()
    await get_baseline_s2().aclose()


app = FastAPI(title="MARS Baseline", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.dependency_overrides[get_gemini] = get_baseline_gemini
app.dependency_overrides[get_pipeline] = get_restored_baseline_pipeline
app.dependency_overrides[get_s2] = get_baseline_s2
app.include_router(query_router)
