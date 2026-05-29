from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def leiden_partition(
    adjacency: sp.csr_matrix,
    *,
    resolution: float,
    n_iterations: int,
    seed: int | None,
    use_weights: bool,
) -> np.ndarray:
    """Assign every node to a community with Leiden on an affinity graph."""
    graph = to_igraph(adjacency, use_weights=use_weights)
    partition = run_leiden(
        graph,
        resolution=resolution,
        n_iterations=n_iterations,
        seed=seed,
        use_weights=use_weights,
    )
    return np.asarray(partition.membership, dtype=np.int64)


def to_igraph(adjacency: sp.csr_matrix, *, use_weights: bool):
    """Convert the upper triangle of an adjacency to an undirected igraph graph."""
    try:
        import igraph as ig
    except ImportError as e:
        raise ImportError(
            "Missing optional dependency 'igraph'. Install with: uv add igraph"
        ) from e

    upper = sp.triu(adjacency, k=1).tocoo()
    edges = list(zip(upper.row.tolist(), upper.col.tolist()))
    graph = ig.Graph(n=int(adjacency.shape[0]), edges=edges, directed=False)
    if use_weights:
        graph.es["weight"] = upper.data.tolist()
    return graph


def run_leiden(
    graph,
    *,
    resolution: float,
    n_iterations: int,
    seed: int | None,
    use_weights: bool,
):
    """Run Leiden with a resolution-based configuration model partition."""
    try:
        import leidenalg
    except ImportError as e:
        raise ImportError(
            "Missing optional dependency 'leidenalg'. Install with: uv add leidenalg"
        ) from e

    kwargs = {
        "weights": "weight" if use_weights else None,
        "resolution_parameter": float(resolution),
        "n_iterations": int(n_iterations),
    }
    if seed is not None:
        kwargs["seed"] = int(seed)

    return leidenalg.find_partition(
        graph, leidenalg.RBConfigurationVertexPartition, **kwargs
    )
