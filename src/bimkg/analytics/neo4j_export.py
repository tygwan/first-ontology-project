"""Neo4j CSV export for graph database import.

Produces node and edge CSVs compatible with ``neo4j-admin database import``.
Uses Neo4j's header format with :ID, :LABEL, :TYPE, :START_ID, :END_ID.

Exported relationships:
- ADJACENT_TO (symmetric, from adjacency.parquet)
- HAS_PARENT (from parent_id)
- BELONGS_TO_PIPELINE (PipingComponent → Pipeline)
- IN_ZONE (Object → Zone, from Louvain analysis)
- MUST_PRECEDE (from precedence DAG)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import networkx as nx

from bimkg import config


def export_neo4j(
    gold: pd.DataFrame,
    adjacency: pd.DataFrame,
    precedence_dag: nx.DiGraph | None = None,
    zone_map: dict[str, int] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Export all Neo4j CSVs. Returns {name: path} dict."""
    if output_dir is None:
        output_dir = config.DATA_ONTOLOGY / "neo4j"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    paths["nodes_objects"] = _export_object_nodes(gold, zone_map, output_dir)
    paths["nodes_pipelines"] = _export_pipeline_nodes(gold, output_dir)
    paths["nodes_zones"] = _export_zone_nodes(gold, zone_map, output_dir)
    paths["edges_adjacent"] = _export_adjacent_edges(adjacency, output_dir)
    paths["edges_parent"] = _export_parent_edges(gold, output_dir)
    paths["edges_pipeline"] = _export_pipeline_edges(gold, output_dir)

    if zone_map:
        paths["edges_in_zone"] = _export_zone_edges(zone_map, output_dir)
    if precedence_dag:
        paths["edges_precede"] = _export_precedence_edges(precedence_dag, output_dir)

    return paths


def _export_object_nodes(
    gold: pd.DataFrame,
    zone_map: dict[str, int] | None,
    output_dir: Path,
) -> Path:
    cols = {
        "object_id": "objectId:ID",
        "display_name": "displayName",
        "refined_class": "refinedClass",
        "centroid_x": "centroidX:double",
        "centroid_y": "centroidY:double",
        "centroid_z": "centroidZ:double",
        "dry_weight_kg": "dryWeightKg:double",
        "classification_confidence": "confidence",
    }
    df = gold[list(cols.keys())].rename(columns=cols).copy()

    if zone_map:
        df["zoneId:int"] = gold["object_id"].map(zone_map)

    label_map = {
        "Piping": "BIMObject:PipingComponent",
        "Structure": "BIMObject:StructuralMember",
        "Equipment": "BIMObject:Equipment",
        "Electrical": "BIMObject:ElectricalComponent",
        "HVAC": "BIMObject:HvacComponent",
        "Other": "BIMObject:UncategorizedObject",
    }
    df[":LABEL"] = gold["refined_class"].map(label_map).fillna("BIMObject")
    # Override for containers / analysis volumes
    df.loc[gold["is_container"] == True, ":LABEL"] = "BIMObject:HierarchyNode"
    df.loc[gold["is_analysis_volume"] == True, ":LABEL"] = "AnalysisArtifact:AnalysisVolume"

    path = output_dir / "nodes_objects.csv"
    df.to_csv(path, index=False)
    return path


def _export_pipeline_nodes(gold: pd.DataFrame, output_dir: Path) -> Path:
    pipelines = gold["sp3d_pipeline"].dropna().unique()
    df = pd.DataFrame({
        "pipelineId:ID": [f"pipeline-{p}" for p in sorted(pipelines)],
        "name": sorted(pipelines),
        ":LABEL": "Pipeline",
    })
    path = output_dir / "nodes_pipelines.csv"
    df.to_csv(path, index=False)
    return path


def _export_zone_nodes(
    gold: pd.DataFrame,
    zone_map: dict[str, int] | None,
    output_dir: Path,
) -> Path:
    if not zone_map:
        zones = []
    else:
        zone_ids = sorted(set(zone_map.values()))
        zones = [{"zoneId:ID": f"zone-{z}", "zoneNumber:int": z, ":LABEL": "Zone"}
                 for z in zone_ids]
    df = pd.DataFrame(zones) if zones else pd.DataFrame(
        columns=["zoneId:ID", "zoneNumber:int", ":LABEL"]
    )
    path = output_dir / "nodes_zones.csv"
    df.to_csv(path, index=False)
    return path


def _export_adjacent_edges(adjacency: pd.DataFrame, output_dir: Path) -> Path:
    df = pd.DataFrame({
        ":START_ID": adjacency["source_object_id"],
        ":END_ID": adjacency["target_object_id"],
        ":TYPE": "ADJACENT_TO",
    })
    path = output_dir / "edges_adjacent_to.csv"
    df.to_csv(path, index=False)
    return path


def _export_parent_edges(gold: pd.DataFrame, output_dir: Path) -> Path:
    has_parent = gold[gold["parent_id"].notna() & (gold["parent_id"] != "")]
    valid = has_parent[has_parent["parent_id"].isin(gold["object_id"])]
    df = pd.DataFrame({
        ":START_ID": valid["object_id"],
        ":END_ID": valid["parent_id"],
        ":TYPE": "HAS_PARENT",
    })
    path = output_dir / "edges_has_parent.csv"
    df.to_csv(path, index=False)
    return path


def _export_pipeline_edges(gold: pd.DataFrame, output_dir: Path) -> Path:
    piping = gold[gold["sp3d_pipeline"].notna()]
    df = pd.DataFrame({
        ":START_ID": piping["object_id"],
        ":END_ID": [f"pipeline-{p}" for p in piping["sp3d_pipeline"]],
        ":TYPE": "BELONGS_TO_PIPELINE",
    })
    path = output_dir / "edges_belongs_to_pipeline.csv"
    df.to_csv(path, index=False)
    return path


def _export_zone_edges(zone_map: dict[str, int], output_dir: Path) -> Path:
    df = pd.DataFrame([
        {":START_ID": oid, ":END_ID": f"zone-{zid}", ":TYPE": "IN_ZONE"}
        for oid, zid in zone_map.items()
    ])
    path = output_dir / "edges_in_zone.csv"
    df.to_csv(path, index=False)
    return path


def _export_precedence_edges(dag: nx.DiGraph, output_dir: Path) -> Path:
    rows = []
    for u, v, data in dag.edges(data=True):
        rows.append({
            ":START_ID": u,
            ":END_ID": v,
            ":TYPE": "MUST_PRECEDE",
            "edgeType": data.get("edge_type", ""),
        })
    df = pd.DataFrame(rows)
    path = output_dir / "edges_must_precede.csv"
    df.to_csv(path, index=False)
    return path
