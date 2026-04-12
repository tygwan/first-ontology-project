"""Construction zone analysis via Louvain community detection.

Provides tunable zone granularity through the ``resolution`` parameter.
Higher resolution → more, smaller zones (better for work packaging).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx


#: Construction class ordering — used for zone-level sequencing.
INSTALL_ORDER: dict[str, int] = {
    "Equipment": 0,
    "Structure": 1,
    "Piping": 2,
    "Electrical": 3,
    "HVAC": 4,
    "Other": 5,
}


def assign_louvain_zones(
    G: nx.Graph,
    resolution: float = 1.0,
    seed: int = 42,
) -> dict[str, int]:
    """Run Louvain community detection and return {object_id: zone_id}."""
    communities = nx.community.louvain_communities(G, resolution=resolution, seed=seed)
    mapping: dict[str, int] = {}
    for zone_id, members in enumerate(communities):
        for node in members:
            mapping[node] = zone_id
    return mapping


def zone_summary(
    gold: pd.DataFrame,
    zone_col: str = "zone_id",
) -> pd.DataFrame:
    """Compute per-zone statistics for construction planning."""
    grouped = gold.groupby(zone_col)
    summary = grouped.agg(
        n_objects=("object_id", "count"),
        n_equipment=("refined_class", lambda s: (s == "Equipment").sum()),
        n_structure=("refined_class", lambda s: (s == "Structure").sum()),
        n_piping=("refined_class", lambda s: (s == "Piping").sum()),
        n_electrical=("refined_class", lambda s: (s == "Electrical").sum()),
        total_weight_kg=("dry_weight_kg", "sum"),
        mean_z=("centroid_z", "mean"),
        n_pipelines=("sp3d_pipeline", "nunique"),
    )
    summary["has_equipment"] = summary["n_equipment"] > 0
    return summary.sort_values("n_objects", ascending=False)


def cross_zone_edges(
    adjacency: pd.DataFrame,
    zone_map: dict[str, int],
) -> tuple[int, int]:
    """Count edges that cross zone boundaries. Returns (cross, total)."""
    cross = 0
    total = 0
    for _, row in adjacency.iterrows():
        s, t = row["source_object_id"], row["target_object_id"]
        zs = zone_map.get(s)
        zt = zone_map.get(t)
        if zs is not None and zt is not None:
            total += 1
            if zs != zt:
                cross += 1
    return cross, total
