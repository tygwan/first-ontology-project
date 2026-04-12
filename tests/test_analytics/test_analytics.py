"""Tests for bimkg.analytics (metrics, zones, precedence, neo4j export)."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd
import pytest

from bimkg import config
from bimkg.analytics.metrics import build_physical_graph, compute_metrics
from bimkg.analytics.zones import (
    INSTALL_ORDER,
    assign_louvain_zones,
    cross_zone_edges,
    zone_summary,
)
from bimkg.analytics.precedence import (
    build_precedence_dag,
    critical_chain_summary,
    find_longest_chain,
)
from bimkg.analytics.neo4j_export import export_neo4j


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gold() -> pd.DataFrame:
    if not config.ENRICHED_OBJECTS.exists():
        pytest.skip("Gold parquet not found")
    return pd.read_parquet(config.ENRICHED_OBJECTS)


@pytest.fixture(scope="module")
def adjacency() -> pd.DataFrame:
    if not config.ENRICHED_ADJACENCY_SYM.exists():
        pytest.skip("Adjacency parquet not found")
    return pd.read_parquet(config.ENRICHED_ADJACENCY_SYM)


@pytest.fixture(scope="module")
def phys_graph(gold, adjacency) -> nx.Graph:
    return build_physical_graph(gold, adjacency)


@pytest.fixture(scope="module")
def zone_map(phys_graph) -> dict[str, int]:
    return assign_louvain_zones(phys_graph, resolution=3.0)


@pytest.fixture(scope="module")
def gold_with_zones(gold, zone_map) -> pd.DataFrame:
    df = gold.copy()
    df["zone_id"] = df["object_id"].map(zone_map)
    return df


@pytest.fixture(scope="module")
def dag(gold_with_zones, adjacency) -> nx.DiGraph:
    return build_precedence_dag(gold_with_zones, adjacency, zone_col="zone_id")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_physical_graph_node_count(self, phys_graph) -> None:
        assert phys_graph.number_of_nodes() == 8511

    def test_physical_graph_excludes_containers(self, gold, phys_graph) -> None:
        container_ids = set(gold[gold["is_container"] == True]["object_id"])
        assert not container_ids & set(phys_graph.nodes())

    def test_compute_metrics_shape(self, phys_graph) -> None:
        m = compute_metrics(phys_graph)
        assert len(m) == phys_graph.number_of_nodes()
        assert "degree" in m.columns
        assert "degree_centrality" in m.columns
        assert "clustering_coefficient" in m.columns

    def test_degree_nonnegative(self, phys_graph) -> None:
        m = compute_metrics(phys_graph)
        assert (m["degree"] >= 0).all()


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------


class TestZones:
    def test_louvain_covers_all_nodes(self, phys_graph, zone_map) -> None:
        assert set(zone_map.keys()) == set(phys_graph.nodes())

    def test_zone_count_in_range(self, zone_map) -> None:
        n_zones = len(set(zone_map.values()))
        assert 10 <= n_zones <= 200

    def test_cross_zone_edges_less_than_total(self, adjacency, zone_map) -> None:
        cross, total = cross_zone_edges(adjacency, zone_map)
        assert 0 < cross < total

    def test_zone_summary_has_equipment_flag(self, gold_with_zones) -> None:
        phys = gold_with_zones[
            (gold_with_zones["is_container"] == False)
            & (gold_with_zones["is_analysis_volume"] == False)
        ]
        zs = zone_summary(phys, "zone_id")
        assert "has_equipment" in zs.columns

    def test_install_order_has_six_classes(self) -> None:
        assert len(INSTALL_ORDER) == 6


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


class TestPrecedence:
    def test_dag_is_acyclic(self, dag) -> None:
        assert nx.is_directed_acyclic_graph(dag)

    def test_dag_has_nodes(self, dag) -> None:
        assert dag.number_of_nodes() == 8511

    def test_dag_has_edges(self, dag) -> None:
        assert dag.number_of_edges() > 0

    def test_critical_chain_nonempty(self, dag) -> None:
        chain = find_longest_chain(dag)
        assert len(chain) > 10

    def test_critical_chain_summary_columns(self, dag, gold) -> None:
        summary = critical_chain_summary(dag, gold)
        assert "step" in summary.columns
        assert "refined_class" in summary.columns
        assert "edge_type" in summary.columns
        assert "centroid_z" in summary.columns

    def test_edge_types_valid(self, dag) -> None:
        valid = {"class_order", "vertical", "adjacency_interference"}
        for _, _, data in dag.edges(data=True):
            assert data.get("edge_type") in valid


# ---------------------------------------------------------------------------
# Neo4j export
# ---------------------------------------------------------------------------


class TestNeo4jExport:
    def test_export_creates_files(self, gold, adjacency, dag, zone_map, tmp_path) -> None:
        paths = export_neo4j(gold, adjacency, dag, zone_map, tmp_path)
        assert len(paths) >= 7
        for name, p in paths.items():
            assert p.exists(), f"{name} not found"
            assert p.stat().st_size > 0

    def test_nodes_objects_has_label(self, gold, adjacency, tmp_path) -> None:
        paths = export_neo4j(gold, adjacency, output_dir=tmp_path)
        df = pd.read_csv(paths["nodes_objects"])
        assert ":LABEL" in df.columns
        assert df[":LABEL"].notna().all()

    def test_edges_adjacent_count(self, gold, adjacency, tmp_path) -> None:
        paths = export_neo4j(gold, adjacency, output_dir=tmp_path)
        df = pd.read_csv(paths["edges_adjacent"])
        assert len(df) == len(adjacency)

    def test_precedence_edges_have_type(self, gold, adjacency, dag, zone_map, tmp_path) -> None:
        paths = export_neo4j(gold, adjacency, dag, zone_map, tmp_path)
        df = pd.read_csv(paths["edges_precede"])
        assert "edgeType" in df.columns
        assert df["edgeType"].notna().all()
