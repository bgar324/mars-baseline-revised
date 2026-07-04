import asyncio
from collections import Counter
from typing import Any

import hdbscan
import numpy as np
from loguru import logger

from mars.config.pipeline import (
    ClusterAlgorithm,
    ClusterConfig,
    Normalization,
    resolve_mcs,
)
from mars.models.s2 import Paper
from mars.pipeline.cluster.knn import build_knn
from mars.pipeline.cluster.leiden import leiden_partition
from mars.pipeline.cluster.structure import (
    centroids,
    cluster_sizes,
    merge_centroids,
    select_perspectives,
)
from mars.pipeline.cluster.umap import reduce
from mars.schemas.event import StageName
from mars.workflow.base import BaseNode, BaseStep, WorkflowContext


def paper_counts(clusters: dict[int, list[Paper]] | None) -> dict[int, int]:
    return {
        label: len(papers) for label, papers in (clusters or {}).items() if label != -1
    }


def cluster_papers(
    papers: list[Paper],
    config: ClusterConfig | None = None,
) -> dict[int, list[Paper]]:
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

    if cfg.merge.enabled:
        labels = merge_clusters(embeddings, labels, cfg.merge.n_clusters)

    clusters: dict[int, list[Paper]] = {}
    for paper, label in zip(embedded, labels):
        clusters.setdefault(int(label), []).append(paper)
    return clusters


def merge_clusters(
    features: np.ndarray, labels: np.ndarray, n_clusters: int
) -> np.ndarray:
    centers = centroids(features, labels)
    if len(centers) <= n_clusters:
        return labels

    sizes = cluster_sizes(labels)
    members = {label: np.where(labels == label)[0].tolist() for label in centers}
    _, _, merged_members = merge_centroids(
        centers, sizes, members, n_clusters=n_clusters
    )

    out = np.full_like(labels, -1)
    for new_label, indices in enumerate(merged_members.values()):
        out[indices] = new_label
    return out


def cluster_hdbscan(
    projection: np.ndarray, cfg: ClusterConfig, n_papers: int
) -> np.ndarray:
    mcs = resolve_mcs(cfg.hdbscan, n_papers)
    return hdbscan.HDBSCAN(
        min_cluster_size=mcs,
        min_samples=cfg.hdbscan.min_samples,
        metric=cfg.hdbscan.metric,
        cluster_selection_method=cfg.hdbscan.method,
    ).fit_predict(projection)


def cluster_leiden(projection: np.ndarray, cfg: ClusterConfig) -> np.ndarray:
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
    labels = labels.copy()
    counts = Counter(labels.tolist())
    large = [c for c, n in counts.items() if n >= mcs]
    small = [c for c, n in counts.items() if n < mcs]
    if not large or not small:
        return relabel_contiguous(labels)

    centers = np.array([coords[labels == c].mean(axis=0) for c in large])
    for i in np.where(np.isin(labels, small))[0]:
        nearest = int(np.linalg.norm(centers - coords[i], axis=1).argmin())
        labels[i] = large[nearest]
    return relabel_contiguous(labels)


def relabel_contiguous(labels: np.ndarray) -> np.ndarray:
    out = labels.copy()
    remap: dict[int, int] = {}
    for old in sorted(set(labels.tolist())):
        remap[old] = len(remap)
    for old, new in remap.items():
        out[labels == old] = new
    return out


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if float(norms.min()) <= 0.0:
        raise ValueError("zero-norm vector in embedding matrix")
    return matrix / norms


def center_and_normalize(matrix: np.ndarray) -> np.ndarray:
    centered = matrix - matrix.mean(axis=0)
    return l2_normalize(centered)


def normalize_embeddings(matrix: np.ndarray, mode: Normalization) -> np.ndarray:
    if mode is Normalization.L2:
        return l2_normalize(matrix)
    if mode is Normalization.CENTER_L2:
        return center_and_normalize(matrix)
    raise ValueError(f"unknown normalization mode: {mode}")


clog = logger.bind(source="workflow.cluster", stage="cluster")

CLUSTER_LOCK = asyncio.Lock()


class ClusterPapersStep(BaseStep):
    name = "cluster.cluster_papers"
    event = "clusters.generated"
    requires = ()

    def __init__(
        self, config: ClusterConfig | None = None, *, enabled: bool = True
    ) -> None:
        super().__init__(enabled=enabled)
        self._config = config

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        async with CLUSTER_LOCK:
            clog.info("lock | acquired, clustering {} papers", len(ctx.papers))
            ctx.clusters = await asyncio.to_thread(
                cluster_papers, ctx.papers, self._config
            )
            clog.info(
                "lock | released, {} clusters", len(ctx.clusters or {})
            )
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        sizes = paper_counts(ctx.clusters)
        return {"clusters": len(sizes), "sizes": sizes}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        sizes = paper_counts(ctx.clusters)
        return f"{len(sizes)} clusters {sizes}"


class SelectPerspectivesStep(BaseStep):
    name = "cluster.select_perspectives"
    event = "perspectives.selected"
    requires = ("cluster.cluster_papers",)

    def __init__(self, n_select: int = 3, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self._n_select = n_select

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        clusters = ctx.clusters or {}
        labels = sorted(k for k in clusters if k != -1)
        if not labels:
            ctx.perspectives = []
            return ctx

        centers = np.stack(
            [
                np.array(
                    [p.specter_v2 for p in clusters[label]], dtype=np.float32
                ).mean(axis=0)
                for label in labels
            ]
        )
        selected = select_perspectives(centers, n_select=self._n_select)
        ctx.perspectives = [labels[i] for i in selected]
        return ctx

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"perspectives": ctx.perspectives or []}

    def log_message(self, ctx: WorkflowContext) -> str | None:
        return f"{len(ctx.perspectives or [])} perspectives {ctx.perspectives}"


class ClusterNode(BaseNode):
    def __init__(
        self, *, config: ClusterConfig | None = None, n_select: int = 3
    ) -> None:
        super().__init__(
            stage=StageName.CLUSTER,
            name="cluster",
            steps=[
                ClusterPapersStep(config),
                SelectPerspectivesStep(n_select),
            ],
        )

    def summarize(self, ctx: WorkflowContext) -> dict[str, Any]:
        sizes = paper_counts(ctx.clusters)
        return {"clusters": len(sizes), "perspectives": ctx.perspectives or []}
