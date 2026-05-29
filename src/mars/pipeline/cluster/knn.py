from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from sklearn.neighbors import NearestNeighbors


def build_knn(
    features: np.ndarray,
    *,
    k: int,
    symmetrize_mode: str = "max",
) -> sp.csr_matrix:
    """Build a symmetric kNN affinity graph from a feature matrix.

    Edge weights are cosine affinities (1 - cosine distance) clipped to [0, 1],
    with a zero diagonal.
    """
    n = int(features.shape[0])
    neighbors = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(features)
    distances, indices = neighbors.kneighbors(features, return_distance=True)
    distances, indices = distances[:, 1:], indices[:, 1:]

    rows = np.repeat(np.arange(n, dtype=np.int32), k)
    cols = indices.reshape(-1).astype(np.int32)
    affinity = np.clip(1.0 - distances.reshape(-1), 0.0, 1.0).astype(np.float32)

    directed = sp.csr_matrix((affinity, (rows, cols)), shape=(n, n), dtype=np.float32)
    directed.sum_duplicates()

    adjacency = symmetrize(directed, symmetrize_mode)
    adjacency.setdiag(0.0)
    adjacency.eliminate_zeros()
    return adjacency


def symmetrize(directed: sp.csr_matrix, mode: str) -> sp.csr_matrix:
    """Convert a directed kNN graph into an undirected adjacency."""
    if mode == "max":
        return directed.maximum(directed.T).tocsr()
    if mode == "mean":
        return ((directed + directed.T) * 0.5).tocsr()
    raise ValueError(f"unsupported symmetrize_mode: {mode}")
