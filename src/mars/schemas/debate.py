from pydantic import BaseModel, Field

from mars.models.persona import PersonaAgent
from mars.models.s2 import Paper


class DebateRequest(BaseModel):
    focal_claim: str
    agents: list[PersonaAgent]
    cluster_papers: dict[str, list[Paper]] = Field(default_factory=dict)
