"""Graph metrics for BIM adjacency network.

Computes degree centrality, betweenness centrality, and clustering
coefficient for physical objects in the adjacency graph.
"""

from __future__ import annotations

import pandas as pd
import networkx as nx


def build_physical_graph(
    gold: pd.DataFrame,
    adjacency: pd.DataFrame,
) -> nx.Graph:
    """Build undirected graph from physical objects only."""
    phys_ids = set(
        gold.loc[
            (gold["is_container"] == False) & (gold["is_analysis_volume"] == False),
            "object_id",
        ]
    )
    adj_phys = adjacency[
        adjacency["source_object_id"].isin(phys_ids)
        & adjacency["target_object_id"].isin(phys_ids)
    ]
    G = nx.from_pandas_edgelist(adj_phys, "source_object_id", "target_object_id")
    for oid in phys_ids:
        if oid not in G:
            G.add_node(oid)
    return G


def compute_metrics(G: nx.Graph) -> pd.DataFrame:
    """Compute per-node graph metrics. Returns DataFrame indexed by object_id."""
    degree = pd.Series(dict(G.degree()), name="degree")
    deg_cent = pd.Series(nx.degree_centrality(G), name="degree_centrality")
    clustering = pd.Series(nx.clustering(G), name="clustering_coefficient")

    df = pd.DataFrame({"degree": degree, "degree_centrality": deg_cent,
                        "clustering_coefficient": clustering})
    df.index.name = "object_id"
    return df
