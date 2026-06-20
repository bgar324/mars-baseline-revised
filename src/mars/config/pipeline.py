from enum import Enum

from pydantic import BaseModel, Field


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
    snippets_per_anchor: int = Field(default=50, ge=1, le=1000)
    retrieval_budget: int = Field(default=300, ge=1)
    publication_types: list[PublicationType] = Field(
        default_factory=lambda: list(PublicationType)
    )
    min_citation_count: int = Field(default=1, ge=1)
    target_corpus_size: int = Field(
        default=150,
        ge=1,
        description=(
            "Expand via recommendations until at least this many distinct papers "
            "are retrieved, so clustering has enough material for diverse personas."
        ),
    )
    expansion_rounds: int = Field(
        default=0,
        ge=0,
        description=(
            "Max recommendation-based expansion rounds when below "
            "target_corpus_size. Default 0: breadth comes from diverse "
            "hypothetical-question anchors, not citation recommendations."
        ),
    )
    expansion_seed_size: int = Field(
        default=40,
        ge=1,
        description="Top-cited papers used to seed each expansion round.",
    )
    expansion_limit: int = Field(
        default=100, ge=1, description="Papers requested per recommendation round."
    )


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


class KNNConfig(BaseModel):
    k: int = Field(default=15, ge=2, le=200)
    symmetrize_mode: str = "max"


class LeidenConfig(BaseModel):
    resolution: float = Field(default=1.0, gt=0.0)
    n_iterations: int = -1
    seed: int | None = 42
    use_weights: bool = True
    mcs: int = Field(
        default=15,
        ge=2,
        description=(
            "Minimum papers per surviving cluster. Smaller communities are merged "
            "into their nearest surviving community."
        ),
    )


class Normalization(str, Enum):
    L2 = "l2"
    CENTER_L2 = "center_l2"


class ClusterAlgorithm(str, Enum):
    HDBSCAN = "hdbscan"
    LEIDEN = "leiden"


class MergeConfig(BaseModel):
    enabled: bool = False
    n_clusters: int = 4


class ClusterConfig(BaseModel):
    algorithm: ClusterAlgorithm = ClusterAlgorithm.LEIDEN
    umap: UMAPConfig = Field(default_factory=UMAPConfig)
    hdbscan: HDBSCANConfig = Field(default_factory=HDBSCANConfig)
    knn: KNNConfig = Field(default_factory=KNNConfig)
    leiden: LeidenConfig = Field(default_factory=LeidenConfig)
    normalization: Normalization = Normalization.L2
    merge: MergeConfig = Field(default_factory=MergeConfig)


class PipelineConfig(BaseModel):
    document_extraction: DocumentExtractionConfig = Field(
        default_factory=DocumentExtractionConfig
    )
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    clustering: ClusterConfig = Field(default_factory=ClusterConfig)


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
