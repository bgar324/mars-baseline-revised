import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mars.api.dependencies import get_s2
from mars.api.router import debate_router, query_router

logging.getLogger("absl").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await get_s2().aclose()


app = FastAPI(title="MARS", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(query_router)
app.include_router(debate_router)
