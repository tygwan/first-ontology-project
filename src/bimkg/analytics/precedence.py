"""Construction precedence analysis — DAG + longest chain.

Builds a directed acyclic graph of "must-precede" relationships between
physical objects, based on three types of constraints:

1. **Class order**: Equipment → Structure → Piping → Electrical → HVAC
   (within the same zone, heavier class installs first)
2. **Vertical order**: Lower elevation first (foundations before upper)
   (within the same zone and class)
3. **Adjacency interference**: Adjacent objects of the same class cannot
   be installed simultaneously — lower-elevation one goes first.

The longest path in this DAG is the **structural critical path**: the
minimum number of sequential installation steps even with infinite resources.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import networkx as nx

from bimkg.analytics.zones import INSTALL_ORDER

#: Vertical binning resolution (meters). Objects within the same bin
#: are considered "same elevation" and don't create vertical precedence.
VERTICAL_BIN_M: float = 3.0


def _filter_adjacency_by_tier(
    adjacency: pd.DataFrame,
    tier: str = "strong_medium",
) -> pd.DataFrame:
    """Filter adjacency edges by connection quality tier.

    Tiers (Finding M2):
    - "strong": touch only (13K edges — physical contact)
    - "strong_medium": touch + small overlap <0.01 m³ (87K — default)
    - "all": no filtering (220K — includes BB noise)
    """
    if tier == "all":
        return adjacency
    if tier == "strong":
        return adjacency[adjacency["relation_type"] == "touch"]
    # strong_medium (default)
    mask_strong = adjacency["relation_type"] == "touch"
    mask_medium = (
        (adjacency["relation_type"] == "overlap")
        & (adjacency["overlap_volume_m3"] < 0.01)
    )
    return adjacency[mask_strong | mask_medium]


def build_precedence_dag(
    gold: pd.DataFrame,
    adjacency: pd.DataFrame,
    zone_col: str = "zone_id",
    adjacency_tier: str = "strong_medium",
) -> nx.DiGraph:
    """Build a precedence DAG from physical objects.

    Parameters
    ----------
    adjacency_tier : str
        "strong", "strong_medium" (default), or "all".
        Controls which adjacency edges create interference constraints.

    Edges go from predecessor → successor (predecessor must install first).
    Each edge has an ``edge_type`` attribute: "class_order", "vertical", or
    "adjacency_interference".
    """
    adjacency = _filter_adjacency_by_tier(adjacency, adjacency_tier)

    if "graph_participant" in gold.columns:
        phys = gold[gold["graph_participant"] == True].copy()
    else:
        phys = gold[
            (gold["is_container"] == False) & (gold["is_analysis_volume"] == False)
        ].copy()
    phys["install_rank"] = phys["refined_class"].map(INSTALL_ORDER).fillna(5)
    phys["z_bin"] = (phys["centroid_z"] / VERTICAL_BIN_M).round().astype(int)

    dag = nx.DiGraph()
    for oid in phys["object_id"]:
        dag.add_node(oid)

    _add_class_order_edges(dag, phys, zone_col)
    _add_vertical_edges(dag, phys, zone_col)
    _add_adjacency_interference_edges(dag, phys, adjacency)

    _break_cycles(dag)

    return dag


def _add_class_order_edges(
    dag: nx.DiGraph, phys: pd.DataFrame, zone_col: str
) -> None:
    """Within each zone, equipment precedes structure precedes piping etc."""
    for zone_id, group in phys.groupby(zone_col):
        ranks = group[["object_id", "install_rank"]].drop_duplicates("install_rank")
        ranks = ranks.sort_values("install_rank")
        rank_values = sorted(group["install_rank"].unique())

        for i in range(len(rank_values) - 1):
            earlier_rank = rank_values[i]
            later_rank = rank_values[i + 1]
            earlier_objs = group[group["install_rank"] == earlier_rank]["object_id"]
            later_objs = group[group["install_rank"] == later_rank]["object_id"]
            # One representative edge per class transition per zone
            # (not all-to-all, which would be O(n²))
            rep_earlier = earlier_objs.iloc[0]
            rep_later = later_objs.iloc[0]
            if not dag.has_edge(rep_earlier, rep_later):
                dag.add_edge(rep_earlier, rep_later, edge_type="class_order")


def _add_vertical_edges(
    dag: nx.DiGraph, phys: pd.DataFrame, zone_col: str
) -> None:
    """Within each zone+class, lower elevation precedes higher."""
    for (zone_id, cls), group in phys.groupby([zone_col, "refined_class"]):
        if len(group) < 2:
            continue
        z_bins = sorted(group["z_bin"].unique())
        if len(z_bins) < 2:
            continue
        for i in range(len(z_bins) - 1):
            lower_objs = group[group["z_bin"] == z_bins[i]]["object_id"]
            upper_objs = group[group["z_bin"] == z_bins[i + 1]]["object_id"]
            rep_lower = lower_objs.iloc[0]
            rep_upper = upper_objs.iloc[0]
            if not dag.has_edge(rep_lower, rep_upper):
                dag.add_edge(rep_lower, rep_upper, edge_type="vertical")


def _add_adjacency_interference_edges(
    dag: nx.DiGraph,
    phys: pd.DataFrame,
    adjacency: pd.DataFrame,
) -> None:
    """Adjacent objects of the same class: lower z goes first."""
    phys_map = phys.set_index("object_id")[["refined_class", "centroid_z"]].to_dict("index")
    phys_ids = set(phys["object_id"])

    seen = set()
    for _, row in adjacency.iterrows():
        s, t = row["source_object_id"], row["target_object_id"]
        if s not in phys_ids or t not in phys_ids:
            continue
        pair = (min(s, t), max(s, t))
        if pair in seen:
            continue
        seen.add(pair)

        s_info = phys_map.get(s)
        t_info = phys_map.get(t)
        if s_info is None or t_info is None:
            continue
        if s_info["refined_class"] != t_info["refined_class"]:
            continue

        sz, tz = s_info["centroid_z"], t_info["centroid_z"]
        if abs(sz - tz) < 0.01:
            continue
        if sz < tz:
            first, second = s, t
        else:
            first, second = t, s
        if not dag.has_edge(first, second):
            dag.add_edge(first, second, edge_type="adjacency_interference")


def _break_cycles(dag: nx.DiGraph) -> None:
    """Remove back-edges if any cycles were introduced."""
    while not nx.is_directed_acyclic_graph(dag):
        cycle = nx.find_cycle(dag)
        dag.remove_edge(*cycle[-1][:2])


def find_longest_chain(dag: nx.DiGraph) -> list[str]:
    """Find the longest path in the DAG (critical chain)."""
    return nx.dag_longest_path(dag)


def critical_chain_summary(
    dag: nx.DiGraph,
    gold: pd.DataFrame,
) -> pd.DataFrame:
    """Return a DataFrame describing the critical chain objects."""
    chain = find_longest_chain(dag)
    if not chain:
        return pd.DataFrame()

    gold_idx = gold.set_index("object_id")
    rows = []
    for i, oid in enumerate(chain):
        info = gold_idx.loc[oid] if oid in gold_idx.index else pd.Series()
        edge_type = ""
        if i > 0:
            edge_data = dag.edges[chain[i - 1], oid]
            edge_type = edge_data.get("edge_type", "")
        rows.append({
            "step": i,
            "object_id": oid,
            "display_name": info.get("display_name", ""),
            "refined_class": info.get("refined_class", ""),
            "centroid_z": info.get("centroid_z", None),
            "zone_id": info.get("zone_id", None),
            "edge_type": edge_type,
        })
    return pd.DataFrame(rows)
