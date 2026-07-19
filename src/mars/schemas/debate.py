from pydantic import BaseModel, Field

from mars.models.persona import Persona
from mars.models.s2 import Paper


class DebateRequest(BaseModel):
    focal_claim: str
    agents: list[Persona]
    cluster_papers: dict[str, list[Paper]] = Field(default_factory=dict)
    query_id: str | None = None
    problem: str | None = None


class BaselineChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    agent_ids: list[str] = Field(min_length=1, max_length=1)
