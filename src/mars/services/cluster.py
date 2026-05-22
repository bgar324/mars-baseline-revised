import hdbscan
import numpy as np
import umap

from mars.config.pipeline import ClusterConfig, resolve_mcs
from mars.models.s2 import Paper


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
