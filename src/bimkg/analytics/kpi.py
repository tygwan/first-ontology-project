"""Construction Management + Facility KPI computation.

Produces 33 KPIs at 4 levels (object, zone, pipeline, plant) from Gold
parquet + adjacency data. Covers both construction (BOM, lift, sequence)
and facility (criticality, corrosion, accessibility, valve isolation).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx

from bimkg.analytics.metrics import build_physical_graph


# ===================================================================
# Object-level KPIs
# ===================================================================


def compute_equipment_criticality(
    gold: pd.DataFrame,
    adjacency: pd.DataFrame,
) -> pd.Series:
    """Equipment criticality = normalized(degree × pipeline_crossings).

    High criticality = many neighbors AND sits at pipeline junctions.
    """
    G = build_physical_graph(gold, adjacency)
    degree = pd.Series(dict(G.degree()), name="degree")

    # Count distinct pipelines among neighbors
    pipeline_map = dict(zip(gold["object_id"], gold["sp3d_pipeline"]))
    pipeline_crossings = {}
    for node in G.nodes():
        neighbor_pipelines = set()
        for neighbor in G.neighbors(node):
            p = pipeline_map.get(neighbor)
            if pd.notna(p):
                neighbor_pipelines.add(p)
        pipeline_crossings[node] = len(neighbor_pipelines)

    pc = pd.Series(pipeline_crossings, name="pipeline_crossings")
    raw = degree * (1 + pc)
    score = raw / raw.max() if raw.max() > 0 else raw
    score.name = "equipment_criticality_score"
    return score


def compute_accessibility_index(
    gold: pd.DataFrame,
    adjacency: pd.DataFrame,
) -> pd.Series:
    """Maintenance accessibility = 1 / (1 + neighbor_count_within_5m).

    Low index = crowded surroundings = hard to access for maintenance.
    Uses spatial proximity (centroid distance ≤ 5m), not adjacency graph.
    """
    phys = gold[gold["graph_participant"] == True].copy()
    coords = phys[["object_id", "centroid_x", "centroid_y", "centroid_z"]].set_index("object_id")

    RADIUS = 5.0  # meters
    counts = {}
    coord_arr = coords.values
    ids = coords.index.tolist()

    for i in range(len(ids)):
        dist = np.sqrt(((coord_arr - coord_arr[i]) ** 2).sum(axis=1))
        n_nearby = (dist <= RADIUS).sum() - 1  # exclude self
        counts[ids[i]] = n_nearby

    raw = pd.Series(counts)
    index = 1.0 / (1.0 + raw)
    index.name = "maintenance_accessibility_index"
    return index


def compute_corrosion_risk(gold: pd.DataFrame) -> pd.Series:
    """Corrosion risk = normalized(pressure × temperature × material_factor).

    material_factor: Carbon Steel = 1.0, Stainless = 0.3, others = 0.5.
    Only computed for objects with both pressure and temperature data.
    """
    MATERIAL_FACTORS = {
        "Carbon Steel": 1.0,
        "Stainless Steel": 0.3,
    }
    DEFAULT_FACTOR = 0.5

    df = gold[["object_id", "design_pressure_kpa", "design_temperature_c", "sp3d_material"]].copy()
    df["mat_factor"] = df["sp3d_material"].map(MATERIAL_FACTORS).fillna(DEFAULT_FACTOR)

    has_data = df["design_pressure_kpa"].notna() & df["design_temperature_c"].notna()
    raw = pd.Series(0.0, index=gold["object_id"])

    p = df.loc[has_data, "design_pressure_kpa"].clip(lower=0)
    t = df.loc[has_data, "design_temperature_c"].clip(lower=0)
    m = df.loc[has_data, "mat_factor"]
    score = p * t * m

    if score.max() > 0:
        score = score / score.max()

    raw.loc[df.loc[has_data, "object_id"].values] = score.values
    raw.name = "corrosion_risk_index"
    raw.index.name = "object_id"
    return raw


def compute_valve_isolation(
    gold: pd.DataFrame,
    adjacency: pd.DataFrame,
) -> pd.DataFrame:
    """Identify isolation valves and their isolation section sizes.

    A valve is a piping object whose display_name contains "Valve".
    An isolation section is the set of objects reachable from a valve's
    neighbors within the same pipeline, without crossing another valve.
    """
    piping = gold[
        (gold["refined_class"] == "Piping") & (gold["graph_participant"] == True)
    ].copy()
    pipe_ids = set(piping["object_id"])

    # Build piping-only subgraph
    adj_piping = adjacency[
        adjacency["source_object_id"].isin(pipe_ids)
        & adjacency["target_object_id"].isin(pipe_ids)
    ]
    G = nx.from_pandas_edgelist(adj_piping, "source_object_id", "target_object_id")

    # Identify isolation devices (valves, blind flanges, spectacle blinds)
    ISOLATION_PATTERNS = ("valve", "blind flange", "blind", "spectacle")
    name_map = dict(zip(gold["object_id"], gold["display_name"]))
    valve_ids = set()
    for oid in pipe_ids:
        name = str(name_map.get(oid, "")).lower()
        if any(p in name for p in ISOLATION_PATTERNS):
            valve_ids.add(oid)

    # For each valve, compute isolation section (BFS without crossing valves)
    results = []
    for vid in valve_ids:
        section = set()
        queue = list(G.neighbors(vid)) if vid in G else []
        visited = {vid}
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            if node in valve_ids:
                continue  # don't cross another valve
            section.add(node)
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    queue.append(neighbor)

        results.append({
            "object_id": vid,
            "is_isolation_valve": True,
            "isolation_section_size": len(section),
        })

    if not results:
        return pd.DataFrame(columns=["object_id", "is_isolation_valve", "isolation_section_size"])

    return pd.DataFrame(results)


# ===================================================================
# Zone-level KPIs
# ===================================================================


def compute_zone_kpis(
    gold: pd.DataFrame,
    zone_map: dict[str, int],
    object_kpis: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate object KPIs to zone level."""
    phys = gold[gold["graph_participant"] == True].copy()
    phys["zone_id"] = phys["object_id"].map(zone_map)
    phys = phys.merge(object_kpis, on="object_id", how="left")

    grouped = phys.groupby("zone_id")
    zdf = grouped.agg(
        zone_object_count=("object_id", "count"),
        zone_total_weight_kg=("dry_weight_kg", "sum"),
        zone_equipment_count=("refined_class", lambda s: (s == "Equipment").sum()),
        zone_mean_corrosion_risk=("corrosion_risk_index", "mean"),
        zone_mean_accessibility=("maintenance_accessibility_index", "mean"),
    )

    # Critical equipment count
    if "equipment_criticality_score" in phys.columns:
        threshold = phys["equipment_criticality_score"].quantile(0.9)
        zdf["zone_critical_equipment_count"] = grouped.apply(
            lambda g: (g["equipment_criticality_score"] > threshold).sum()
        )
    else:
        zdf["zone_critical_equipment_count"] = 0

    # Shutdown impact: pipelines affected
    pipe_map = dict(zip(gold["object_id"], gold["sp3d_pipeline"]))
    phys["pipeline"] = phys["object_id"].map(pipe_map)
    zdf["zone_shutdown_impact"] = phys.groupby("zone_id")["pipeline"].nunique()

    return zdf


# ===================================================================
# Pipeline-level KPIs
# ===================================================================


def compute_pipeline_kpis(
    gold: pd.DataFrame,
    zone_map: dict[str, int],
    valve_df: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate KPIs to pipeline level."""
    piping = gold[gold["sp3d_pipeline"].notna()].copy()

    grouped = piping.groupby("sp3d_pipeline")
    pdf = grouped.agg(
        pipeline_object_count=("object_id", "count"),
        pipeline_total_weight_kg=("dry_weight_kg", "sum"),
        pipeline_mean_pressure_kpa=("design_pressure_kpa", "mean"),
        pipeline_mean_temperature_c=("design_temperature_c", "mean"),
    )

    # Zone span
    piping["zone_id"] = piping["object_id"].map(zone_map)
    pdf["pipeline_zone_span"] = piping.groupby("sp3d_pipeline")["zone_id"].nunique()

    # Valve count & isolation sections
    valve_ids = set(valve_df["object_id"]) if not valve_df.empty else set()
    pipe_for_obj = dict(zip(gold["object_id"], gold["sp3d_pipeline"]))
    valve_pipe = pd.Series({vid: pipe_for_obj.get(vid) for vid in valve_ids}).dropna()
    if not valve_pipe.empty:
        pdf["pipeline_valve_count"] = valve_pipe.value_counts()
        merged_valves = valve_df.merge(
            gold[["object_id", "sp3d_pipeline"]], on="object_id"
        )
        pdf["pipeline_isolation_sections"] = merged_valves.groupby(
            "sp3d_pipeline"
        )["isolation_section_size"].count()
    else:
        pdf["pipeline_valve_count"] = 0
        pdf["pipeline_isolation_sections"] = 0

    pdf["pipeline_valve_count"] = pdf["pipeline_valve_count"].fillna(0).astype(int)
    pdf["pipeline_isolation_sections"] = pdf["pipeline_isolation_sections"].fillna(0).astype(int)

    # Corrosion risk (pipeline mean)
    pdf["pipeline_corrosion_risk"] = (
        pdf["pipeline_mean_pressure_kpa"].fillna(0)
        * pdf["pipeline_mean_temperature_c"].fillna(0)
    )
    max_cr = pdf["pipeline_corrosion_risk"].max()
    if max_cr > 0:
        pdf["pipeline_corrosion_risk"] = pdf["pipeline_corrosion_risk"] / max_cr

    return pdf


# ===================================================================
# Plant-level KPIs
# ===================================================================


def compute_plant_kpis(
    gold: pd.DataFrame,
    zone_kpis: pd.DataFrame,
    pipeline_kpis: pd.DataFrame,
    critical_chain_length: int,
) -> dict:
    """Compute plant-level summary KPIs."""
    phys = gold[gold["graph_participant"] == True]
    return {
        "total_objects": len(gold),
        "total_physical_objects": len(phys),
        "total_weight_tonnes": phys["dry_weight_kg"].sum() / 1000,
        "critical_chain_length": critical_chain_length,
        "max_parallel_zones": _count_max_parallel(zone_kpis),
        "high_criticality_equipment": int(
            zone_kpis["zone_critical_equipment_count"].sum()
        ),
        "high_corrosion_pipelines": int(
            (pipeline_kpis["pipeline_corrosion_risk"] > 0.7).sum()
        ),
        "low_accessibility_zones": int(
            (zone_kpis["zone_mean_accessibility"] < 0.2).sum()
        ),
    }


def _count_max_parallel(zone_kpis: pd.DataFrame) -> int:
    """Estimate max zones that can proceed in parallel (no dependency)."""
    # Simple heuristic: zones with no shutdown impact overlap
    # A proper calculation would use the zone DAG, but this gives a bound
    return len(zone_kpis)  # upper bound; will be refined with zone DAG
