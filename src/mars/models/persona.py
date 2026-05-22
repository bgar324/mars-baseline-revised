from typing import Literal

from pydantic import BaseModel, Field


ReasoningStyle = Literal[
    "mechanistic",
    "observational",
    "interventional",
    "comparative",
    "theoretical",
    "computational",
    "statistical",
]

EvaluationLens = Literal[
    "internal_validity",
    "external_validity",
    "construct_validity",
    "effect_magnitude",
    "replicability",
    "convergence",
    "predictive_power",
]


class PersonaAgent(BaseModel):
    cluster_id: int
    name: str = Field(description="Archetypal 2-4 word label")
    framing: str = Field(
        description="One sentence on how this cluster frames the focal claim"
    )
    background: str = Field(description="Methodological tradition and evidence base")
    reasoning_style: ReasoningStyle
    evaluation_lens: EvaluationLens
    references: list[str] = Field(description="Paper IDs anchoring the persona")
    instructions: list[str] = Field(
        description="Behavioral rules for debate",
        min_length=3,
        max_length=5,
    )
    constraints: str | None = None
