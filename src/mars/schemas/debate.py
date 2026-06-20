from pydantic import BaseModel, Field

from mars.models.persona import Persona
from mars.models.s2 import Paper


class DebateRequest(BaseModel):
    focal_claim: str
    agents: list[Persona]
    cluster_papers: dict[str, list[Paper]] = Field(default_factory=dict)
    query_id: str | None = None
    problem: str | None = None
