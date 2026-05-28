from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    document_extraction: DocumentExtractionConfig = Field(
        default_factory=lambda: DocumentExtractionConfig()
    )
    retrieval: RetrievalConfig = Field(default_factory=lambda: RetrievalConfig())
    clustering: ClusterConfig = Field(default_factory=lambda: ClusterConfig())


class SectionConfig(BaseModel):
    extraction_passes: int = Field(ge=1, le=10)
    max_char_buffer: int = Field(ge=100, le=5000)


class DocumentExtractionConfig(BaseModel):
    sections: dict[str, SectionConfig] = Field(
        default_factory=lambda: {
            "introduction": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "related_work": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "methods": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "experiments": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "results": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "discussion": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "conclusion": SectionConfig(extraction_passes=1, max_char_buffer=1500),
            "default": SectionConfig(extraction_passes=1, max_char_buffer=1500),
        }
    )

    patterns: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "introduction": ["introduction", "intro", "background", "motivation"],
            "related_work": [
                "related work",
                "related works",
                "literature review",
                "prior work",
                "previous work",
            ],
            "methods": [
                "method",
                "methods",
                "methodology",
                "approach",
                "our approach",
                "proposed method",
                "technique",
                "framework",
                "system",
                "architecture",
            ],
            "experiments": [
                "experiment",
                "experiments",
                "experimental setup",
                "evaluation",
                "setup",
            ],
            "results": [
                "result",
                "results",
                "findings",
                "analysis",
                "detailed analysis",
                "overall results",
                "performance",
            ],
            "discussion": ["discussion", "interpretation"],
            "conclusion": [
                "conclusion",
                "conclusions",
                "summary",
                "concluding remarks",
                "future work",
            ],
        }
    )

    max_workers: int = Field(default=5, ge=1, le=20)


class PublicationType(str, Enum):
    JOURNAL_ARTICLE = "JournalArticle"
    CONFERENCE = "Conference"
    STUDY = "Study"
    CLINICAL_TRIAL = "ClinicalTrial"
    CASE_REPORT = "CaseReport"
    META_ANALYSIS = "MetaAnalysis"


class RetrievalConfig(BaseModel):
    papers_per_anchor: int = Field(default=25, ge=1, le=100)
    snippets_per_anchor: int = Field(default=25, ge=1, le=1000)
    retrieval_budget: int = Field(default=300, ge=1)
    publication_types: list[PublicationType] = Field(
        default_factory=lambda: list(PublicationType)
    )
    min_citation_count: int = Field(default=1, ge=1)


class UMAPConfig(BaseModel):
    n_neighbors: int = Field(default=15, ge=2, le=200)
    n_components: int = Field(default=10, ge=2, le=50)
    min_dist: float = Field(default=0.0, ge=0.0, le=1.0)
    metric: str = "cosine"
    random_state: int | None = None


class HDBSCANConfig(BaseModel):
    mcs: int | None = Field(
        default=11,
        ge=2,
        description=(
            "Minimum cluster size. When None, derived from the corpus size "
            "as max(5, n_papers // 30) at clustering time."
        ),
    )
    min_samples: int = Field(default=5, ge=1)
    metric: str = "euclidean"
    method: str = "leaf"


class Normalization(str, Enum):
    L2 = "l2"
    CENTER_L2 = "center_l2"


class ClusterConfig(BaseModel):
    umap: UMAPConfig = Field(default_factory=UMAPConfig)
    hdbscan: HDBSCANConfig = Field(default_factory=HDBSCANConfig)
    normalization: Normalization = Normalization.L2


def normalize_heading(heading: str, patterns: dict[str, list[str]]) -> str:
    heading_lower = heading.lower().strip()
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if pattern in heading_lower:
                return category
    return "default"


def resolve_mcs(config: HDBSCANConfig, n_papers: int) -> int:
    if config.mcs is not None:
        return config.mcs
    return max(5, n_papers // 30)


PipelineConfig.model_rebuild()
