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


class PersonaDraft(BaseModel):
    methods_summary: str = Field(
        description=(
            "List the study designs, data modalities, populations, and model "
            "families shared across the cluster's papers. Name specific datasets, "
            "indices, and statistical methods only in this field. Write this field "
            "before the others."
        )
    )
    name: str = Field(
        description=(
            "Format exactly as '{Field} · {Facet}': a discipline label, a U+00B7 "
            "middle dot surrounded by spaces, then the cluster's distinguishing "
            "facet (method, evaluation lens, scale, or subfocus). Example: "
            "'Social Epidemiologist · Life-Course'."
        )
    )
    framing: str = Field(
        description="One sentence stating how this cluster interprets the focal claim."
    )
    background: str = Field(
        description=(
            "Name the cluster's methodological tradition and the body of evidence "
            "it draws on. State traditions at the family level, not individual "
            "papers."
        )
    )
    reasoning_style: ReasoningStyle
    evaluation_lens: EvaluationLens
    instructions: list[str] = Field(
        description=(
            "Rules governing only how this persona argues during debate. Each entry "
            "is one imperative sentence. Provide 3 to 5 entries."
        ),
        min_length=3,
        max_length=5,
    )


class Persona(PersonaDraft):
    cluster_id: int
    references: list[str] = Field(
        description="Paper IDs of the cluster papers this persona represents."
    )
    constraints: str | None = None
