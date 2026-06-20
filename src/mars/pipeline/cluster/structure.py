from collections.abc import Callable
from itertools import combinations
from typing import Any

import numpy as np


def cluster_centroid(features: np.ndarray) -> np.ndarray:
    return features.mean(axis=0)


def per_cluster(
    labels: np.ndarray, value: Callable[[np.ndarray], Any]
) -> dict[int, Any]:
    return {
        int(label): value(labels == label) for label in np.unique(labels) if label != -1
    }


def centroids(features: np.ndarray, labels: np.ndarray) -> dict[int, np.ndarray]:
    return per_cluster(labels, lambda mask: cluster_centroid(features[mask]))


def cluster_sizes(labels: np.ndarray) -> dict[int, int]:
    return per_cluster(labels, lambda mask: int(np.count_nonzero(mask)))


def centroid_distances(centers: np.ndarray) -> np.ndarray:
    diff = centers[:, None, :] - centers[None, :, :]
    return np.linalg.norm(diff, axis=2)


def closest_pair(centers: dict[int, np.ndarray]) -> tuple[int, int, float]:
    ids = list(centers)
    best = (ids[0], ids[1], np.inf)
    for a, b in combinations(ids, 2):
        distance = float(np.linalg.norm(centers[a] - centers[b]))
        if distance < best[2]:
            best = (a, b, distance)
    return best


def merge_centroids(
    centers: dict[int, np.ndarray],
    sizes: dict[int, int],
    members: dict[int, list[int]],
    *,
    n_clusters: int,
) -> tuple[dict[int, np.ndarray], dict[int, int], dict[int, list[int]]]:
    centers = {k: v.copy() for k, v in centers.items()}
    sizes = dict(sizes)
    members = {k: list(v) for k, v in members.items()}
    next_id = max(centers) + 1 if centers else 0

    while len(centers) > n_clusters:
        a, b, _ = closest_pair(centers)
        size = sizes[a] + sizes[b]
        centers[next_id] = (sizes[a] * centers[a] + sizes[b] * centers[b]) / size
        sizes[next_id] = size
        members[next_id] = members[a] + members[b]
        for stale in (a, b):
            del centers[stale]
            del sizes[stale]
            del members[stale]
        next_id += 1

    return centers, sizes, members


def separation(centers: np.ndarray, subset: tuple[int, ...]) -> float:
    return min(
        float(np.linalg.norm(centers[i] - centers[j]))
        for i, j in combinations(subset, 2)
    )


def select_perspectives(centers: np.ndarray, *, n_select: int) -> tuple[int, ...]:
    n_clusters = centers.shape[0]
    if n_clusters <= n_select:
        return tuple(range(n_clusters))
    return max(
        combinations(range(n_clusters), n_select),
        key=lambda subset: separation(centers, subset),
    )


def prototypes(
    features: np.ndarray,
    members: np.ndarray,
    center: np.ndarray,
    *,
    n_prototypes: int,
) -> np.ndarray:
    distances = np.linalg.norm(features[members] - center, axis=1)
    order = np.argsort(distances)
    return members[order[:n_prototypes]]


def dispersion(features: np.ndarray, center: np.ndarray) -> float:
    return float(np.linalg.norm(features - center, axis=1).mean())


def coherence(features: np.ndarray, labels: np.ndarray) -> dict[int, float]:
    def value(mask: np.ndarray) -> float:
        members = features[mask]
        return dispersion(members, cluster_centroid(members))

    return per_cluster(labels, value)


def variance(features: np.ndarray, labels: np.ndarray) -> dict[int, float]:
    def value(mask: np.ndarray) -> float:
        members = features[mask]
        center = cluster_centroid(members)
        return float(np.square(members - center).sum(axis=1).mean())

    return per_cluster(labels, value)
