import hdbscan
import numpy as np
import umap

from mars.config.pipeline import ClusterConfig, Normalization, resolve_mcs
from mars.models.s2 import Paper


class ClusterService:
    """Pipeline stage service for clustering retrieved papers."""

    def __init__(self, *, config: ClusterConfig | None = None) -> None:
        self._config = config

    def cluster(self, papers: list[Paper]) -> dict[int, list[Paper]]:
        return cluster_papers(papers, self._config)


def cluster_papers(
    papers: list[Paper],
    config: ClusterConfig | None = None,
) -> dict[int, list[Paper]]:
    """Cluster papers into epistemic communities via UMAP + HDBSCAN.

    Returns a mapping of cluster id to papers. Key -1 is the HDBSCAN noise
    cluster. Papers without a SPECTER2 embedding are dropped.
    """
    cfg = config or ClusterConfig()

    embedded = [p for p in papers if p.specter_v2 is not None]
    if not embedded:
        return {}

    embeddings = np.array([p.specter_v2 for p in embedded], dtype=np.float32)
    embeddings = normalize_embeddings(embeddings, cfg.normalization)

    projection = umap.UMAP(
        n_neighbors=cfg.umap.n_neighbors,
        n_components=cfg.umap.n_components,
        min_dist=cfg.umap.min_dist,
        metric=cfg.umap.metric,
        random_state=cfg.umap.random_state,
    ).fit_transform(embeddings)

    mcs = resolve_mcs(cfg.hdbscan, len(embedded))
    labels = hdbscan.HDBSCAN(
        min_cluster_size=mcs,
        min_samples=cfg.hdbscan.min_samples,
        metric=cfg.hdbscan.metric,
        cluster_selection_method=cfg.hdbscan.method,
    ).fit_predict(projection)

    clusters: dict[int, list[Paper]] = {}
    for paper, label in zip(embedded, labels):
        clusters.setdefault(int(label), []).append(paper)
    return clusters


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize rows of an embedding matrix."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if float(norms.min()) <= 0.0:
        raise ValueError("zero-norm vector in embedding matrix")
    return matrix / norms


def center_and_normalize(matrix: np.ndarray) -> np.ndarray:
    """Center on the matrix mean, then L2-normalize.

    Removes the dominant direction shared by all papers in a topic-filtered
    subset, exposing within-topic variance for density-based clustering.
    """
    centered = matrix - matrix.mean(axis=0)
    return l2_normalize(centered)


def normalize_embeddings(matrix: np.ndarray, mode: Normalization) -> np.ndarray:
    """Dispatch to the configured normalization strategy."""
    if mode is Normalization.L2:
        return l2_normalize(matrix)
    if mode is Normalization.CENTER_L2:
        return center_and_normalize(matrix)
    raise ValueError(f"unknown normalization mode: {mode}")
