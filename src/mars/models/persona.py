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

EvidenceRelation = Literal["direct", "analogical", "mixed", "ungrounded"]


class PersonaDraft(BaseModel):
    methods_summary: str = Field(
        description="Designs, data modalities, populations, and model families shared across the cluster."
    )
    evidence_relation: EvidenceRelation = Field(
        description="How the cluster's evidence relates to the focal claim. direct: the papers study "
        "the same system, task, phenomenon, and population as the focal claim. analogical: the papers "
        "study a different system, task, phenomenon, or population and transfer the mechanism by "
        "analogy. mixed: both direct and analogical evidence appear. ungrounded: no cluster evidence "
        "supports the persona."
    )
    role: str = Field(
        description="A plain-language 2 to 3 word research role, such as HCI Researcher or NLP Methodologist."
    )
    perspective: str = Field(
        description="The stable perspective this researcher brings, written in 1 to 2 concise sentences."
    )
    framing: str = Field(
        description="How this cluster interprets the focal claim, in one sentence."
    )
    background: str = Field(
        description="The cluster's methodological tradition and evidence base."
    )
    reasoning_style: ReasoningStyle
    evaluation_lens: EvaluationLens
    instructions: list[str] = Field(
        description="3 to 5 rules for how this persona argues in debate, each one imperative sentence.",
        min_length=3,
        max_length=5,
    )


class Persona(PersonaDraft):
    cluster_id: int
    name: str
    references: list[str] = Field(
        description="Paper IDs of the cluster papers this persona represents."
    )
    constraints: str | None = None
