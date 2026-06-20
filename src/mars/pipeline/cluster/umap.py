import numpy as np


def reduce(
    embeddings: np.ndarray,
    *,
    n_neighbors: int,
    n_components: int,
    min_dist: float,
    metric: str,
    random_state: int | None,
) -> np.ndarray:
    import umap

    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
        init="random",
        n_jobs=-1,
    )
    return np.asarray(reducer.fit_transform(embeddings), dtype=np.float32)
