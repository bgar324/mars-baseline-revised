from collections import Counter

import hdbscan
import numpy as np

from mars.config.pipeline import (
    ClusterAlgorithm,
    ClusterConfig,
    Normalization,
    resolve_mcs,
)
from mars.models.s2 import Paper
from mars.pipeline.cluster.knn import build_knn
from mars.pipeline.cluster.leiden import leiden_partition
from mars.pipeline.cluster.umap import reduce


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
    """Cluster papers into epistemic communities via UMAP + HDBSCAN or Leiden.

    Returns a mapping of cluster id to papers. Key -1 is the noise cluster
    (HDBSCAN only; Leiden assigns every paper). Papers without a SPECTER2
    embedding are dropped.
    """
    cfg = config or ClusterConfig()

    embedded = [p for p in papers if p.specter_v2 is not None]
    if not embedded:
        return {}

    embeddings = np.array([p.specter_v2 for p in embedded], dtype=np.float32)
    embeddings = normalize_embeddings(embeddings, cfg.normalization)

    projection = reduce(
        embeddings,
        n_neighbors=cfg.umap.n_neighbors,
        n_components=cfg.umap.n_components,
        min_dist=cfg.umap.min_dist,
        metric=cfg.umap.metric,
        random_state=cfg.umap.random_state,
    )

    if cfg.algorithm is ClusterAlgorithm.LEIDEN:
        labels = cluster_leiden(projection, cfg)
    else:
        labels = cluster_hdbscan(projection, cfg, len(embedded))

    clusters: dict[int, list[Paper]] = {}
    for paper, label in zip(embedded, labels):
        clusters.setdefault(int(label), []).append(paper)
    return clusters


def cluster_hdbscan(
    projection: np.ndarray, cfg: ClusterConfig, n_papers: int
) -> np.ndarray:
    """Density-cluster the projection with HDBSCAN; label -1 is noise."""
    mcs = resolve_mcs(cfg.hdbscan, n_papers)
    return hdbscan.HDBSCAN(
        min_cluster_size=mcs,
        min_samples=cfg.hdbscan.min_samples,
        metric=cfg.hdbscan.metric,
        cluster_selection_method=cfg.hdbscan.method,
    ).fit_predict(projection)


def cluster_leiden(projection: np.ndarray, cfg: ClusterConfig) -> np.ndarray:
    """Community-detect the projection via a kNN graph and Leiden.

    Every paper is assigned a community; communities smaller than the
    configured minimum are merged into their nearest surviving community.
    """
    k = min(cfg.knn.k, int(projection.shape[0]) - 1)
    adjacency = build_knn(projection, k=k, symmetrize_mode=cfg.knn.symmetrize_mode)
    membership = leiden_partition(
        adjacency,
        resolution=cfg.leiden.resolution,
        n_iterations=cfg.leiden.n_iterations,
        seed=cfg.leiden.seed,
        use_weights=cfg.leiden.use_weights,
    )
    return enforce_min_cluster_size(membership, projection, cfg.leiden.mcs)


def enforce_min_cluster_size(
    labels: np.ndarray, coords: np.ndarray, mcs: int
) -> np.ndarray:
    """Merge undersized communities into their nearest surviving centroid."""
    labels = labels.copy()
    counts = Counter(labels.tolist())
    large = [c for c, n in counts.items() if n >= mcs]
    small = [c for c, n in counts.items() if n < mcs]
    if not large or not small:
        return relabel_contiguous(labels)

    centroids = np.array([coords[labels == c].mean(axis=0) for c in large])
    for i in np.where(np.isin(labels, small))[0]:
        nearest = int(np.linalg.norm(centroids - coords[i], axis=1).argmin())
        labels[i] = large[nearest]
    return relabel_contiguous(labels)


def relabel_contiguous(labels: np.ndarray) -> np.ndarray:
    """Remap cluster ids to a contiguous range starting at 0."""
    out = labels.copy()
    remap: dict[int, int] = {}
    for old in sorted(set(labels.tolist())):
        remap[old] = len(remap)
    for old, new in remap.items():
        out[labels == old] = new
    return out


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
