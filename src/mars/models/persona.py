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


class PersonaSynthesis(BaseModel):
    """Schema the synthesizer fills in. methods_summary leads as a reasoning scratchpad."""

    methods_summary: str = Field(
        description=(
            "Cluster-level summary of common study designs, data modalities, "
            "populations, and model families. Specific datasets, named indices, "
            "and statistical methods belong here only. Reason here first."
        )
    )
    name: str = Field(
        description=(
            "Format '{Field} · {Facet}': discipline label, a middle dot, then the "
            "cluster's distinguishing facet (method/lens/scale/subfocus). "
            "E.g. 'Social Epidemiologist · Life-Course'."
        )
    )
    framing: str = Field(
        description="One sentence on how this community frames the focal claim"
    )
    background: str = Field(
        description="Methodological tradition and evidence base, at the family level"
    )
    reasoning_style: ReasoningStyle
    evaluation_lens: EvaluationLens
    instructions: list[str] = Field(
        description="Debate-behavior rules only",
        min_length=3,
        max_length=5,
    )


class PersonaAgent(BaseModel):
    cluster_id: int
    name: str = Field(
        description="'{Field} · {Facet}' label, e.g. 'Social Epidemiologist · Life-Course'"
    )
    framing: str = Field(
        description="One sentence on how this cluster frames the focal claim"
    )
    background: str = Field(description="Methodological tradition and evidence base")
    methods_summary: str | None = Field(
        default=None,
        description="Cluster-level methods scratchpad from synthesis; unused in debate",
    )
    reasoning_style: ReasoningStyle
    evaluation_lens: EvaluationLens
    references: list[str] = Field(description="Paper IDs anchoring the persona")
    instructions: list[str] = Field(
        description="Behavioral rules for debate",
        min_length=3,
        max_length=5,
    )
    constraints: str | None = None
