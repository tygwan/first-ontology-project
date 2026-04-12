"""Tests for bimkg.ontology.instances (ABox).

Unit tests use small synthetic DataFrames. Integration tests load the
generated ABox files and run SPARQL sanity queries.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS, XSD

from bimkg import config
from bimkg.ontology.namespaces import BIM, INST
from bimkg.ontology.instances import (
    build_objects,
    build_shared,
    build_spatial,
    generate_abox,
)
from bimkg.ontology.schema import generate_tbox


# ---------------------------------------------------------------------------
# Unit tests: build_shared
# ---------------------------------------------------------------------------


class TestBuildShared:
    @pytest.fixture()
    def mini_gold(self) -> pd.DataFrame:
        return pd.DataFrame({
            "sp3d_pipeline": ["P-10147", "P-10147", None],
            "sp3d_pipe_run": ["PR-001", "PR-002", None],
            "level": [6, 7, 8],
            "sp3d_material": ["Carbon Steel", None, "Carbon Steel"],
            "sp3d_spec_name": ["150#", "150#", None],
        })

    def test_pipeline_deduplication(self, mini_gold: pd.DataFrame) -> None:
        g = build_shared(mini_gold)
        pipelines = list(g.subjects(RDF.type, BIM.Pipeline))
        assert len(pipelines) == 1

    def test_piperun_count(self, mini_gold: pd.DataFrame) -> None:
        g = build_shared(mini_gold)
        pipe_runs = list(g.subjects(RDF.type, BIM.PipeRun))
        assert len(pipe_runs) == 2

    def test_level_count(self, mini_gold: pd.DataFrame) -> None:
        g = build_shared(mini_gold)
        levels = list(g.subjects(RDF.type, BIM.Level))
        assert len(levels) == 3

    def test_material_deduplication(self, mini_gold: pd.DataFrame) -> None:
        g = build_shared(mini_gold)
        materials = list(g.subjects(RDF.type, BIM.Material))
        assert len(materials) == 1


# ---------------------------------------------------------------------------
# Unit tests: build_objects typing logic
# ---------------------------------------------------------------------------


class TestBuildObjectsTyping:
    def _make_row(self, **kwargs) -> pd.DataFrame:
        defaults = {
            "object_id": "test-001",
            "refined_class": "Other",
            "is_analysis_volume": False,
            "is_container": False,
            "sp3d_eqp_type_0": None,
            "title_display_name": "Test",
            "system_path": "",
            "level": 6,
            "centroid_x": 0.0,
            "centroid_y": 0.0,
            "centroid_z": 0.0,
            "bbox_volume_m3": 0.0,
            "vertex_count": 0,
            "triangle_count": 0,
            "has_real_mesh": False,
            "classification_confidence": "HIGH",
            "classification_confidence_reason": "xlsx_class_clean",
            "sp3d_pipeline": None,
            "sp3d_pipe_run": None,
            "parent_id": None,
            "sp3d_material": None,
            "sp3d_spec_name": None,
            "sp3d_commodity_code": None,
            "sp3d_npd": None,
            "group_id": None,
            "dry_weight_kg": None,
            "wet_weight_kg": None,
            "length_m": None,
            "design_pressure_kpa": None,
            "design_temperature_c": None,
        }
        defaults.update(kwargs)
        return pd.DataFrame([defaults])

    def test_analysis_volume_typed(self) -> None:
        df = self._make_row(is_analysis_volume=True, refined_class="Piping")
        g = build_objects(df)
        assert (INST["test-001"], RDF.type, BIM.AnalysisVolume) in g

    def test_container_typed_as_hierarchy_node(self) -> None:
        df = self._make_row(is_container=True, refined_class="Structure")
        g = build_objects(df)
        assert (INST["test-001"], RDF.type, BIM.HierarchyNode) in g

    def test_piping_typed(self) -> None:
        df = self._make_row(refined_class="Piping")
        g = build_objects(df)
        assert (INST["test-001"], RDF.type, BIM.PipingComponent) in g

    def test_equipment_with_eqp_type(self) -> None:
        df = self._make_row(
            refined_class="Equipment",
            sp3d_eqp_type_0="Process Equipment",
        )
        g = build_objects(df)
        assert (INST["test-001"], RDF.type, BIM.ProcessEquipment) in g

    def test_equipment_without_eqp_type(self) -> None:
        df = self._make_row(refined_class="Equipment")
        g = build_objects(df)
        assert (INST["test-001"], RDF.type, BIM.UnclassifiedEquipment) in g

    def test_other_typed_as_uncategorized(self) -> None:
        df = self._make_row(refined_class="Other")
        g = build_objects(df)
        assert (INST["test-001"], RDF.type, BIM.UncategorizedObject) in g

    def test_pipeline_link_created(self) -> None:
        df = self._make_row(
            refined_class="Piping",
            sp3d_pipeline="P-10147",
        )
        g = build_objects(df)
        assert (
            INST["test-001"],
            BIM.belongsToPipeline,
            INST["pipeline-P-10147"],
        ) in g

    def test_confidence_property_added(self) -> None:
        df = self._make_row(classification_confidence="LIKELY_BUG")
        g = build_objects(df)
        vals = list(g.objects(INST["test-001"], BIM.classificationConfidence))
        assert str(vals[0]) == "LIKELY_BUG"


# ---------------------------------------------------------------------------
# Unit tests: build_spatial
# ---------------------------------------------------------------------------


class TestBuildSpatial:
    def test_adjacency_triple_count(self) -> None:
        adj = pd.DataFrame({
            "source_object_id": ["a", "b"],
            "target_object_id": ["b", "a"],
        })
        g = build_spatial(adj)
        triples = list(g.triples((None, BIM.adjacentTo, None)))
        assert len(triples) == 2


# ---------------------------------------------------------------------------
# Integration tests: full ABox on real data
# ---------------------------------------------------------------------------


TBOX_PATH = config.ONTOLOGY_OWL
SHARED_PATH = config.ONTOLOGY_OWL_DIR / "bim-shared.ttl"
OBJECTS_PATH = config.ONTOLOGY_OWL_DIR / "bim-objects.ttl"
SPATIAL_PATH = config.ONTOLOGY_OWL_DIR / "bim-spatial.ttl"


@pytest.fixture(scope="module")
def full_graph() -> Graph:
    """Load TBox + all three ABox files into one graph."""
    for p in [TBOX_PATH, SHARED_PATH, OBJECTS_PATH, SPATIAL_PATH]:
        if not p.exists():
            pytest.skip(f"ABox file not found: {p}")
    g = Graph()
    g.parse(str(TBOX_PATH), format="turtle")
    g.parse(str(SHARED_PATH), format="turtle")
    g.parse(str(OBJECTS_PATH), format="turtle")
    g.parse(str(SPATIAL_PATH), format="turtle")
    return g


def _sparql_count(g: Graph, query: str) -> int:
    result = list(g.query(query))
    return int(result[0][0])


class TestIntegrationCounts:
    """Cross-validate SPARQL counts against config expected values."""

    def test_total_triples_reasonable(self, full_graph: Graph) -> None:
        assert len(full_graph) > 400_000

    def test_piping_component_count(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?c) WHERE { ?s a bim:PipingComponent }
        """)
        assert count == 2841

    def test_structural_member_count(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?c) WHERE { ?s a bim:StructuralMember }
        """)
        assert count == 2659

    def test_hierarchy_node_count(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?c) WHERE { ?s a bim:HierarchyNode }
        """)
        assert count == 3353

    def test_analysis_volume_count(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?c) WHERE { ?s a bim:AnalysisVolume }
        """)
        assert count == 145

    def test_equipment_subclass_total(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT (COUNT(?s) AS ?c)
            WHERE { ?s a ?t . ?t rdfs:subClassOf* bim:Equipment }
        """)
        assert count == 715

    def test_pipeline_individuals(self, full_graph: Graph) -> None:
        """147 unique pipelines in AllProperties (K3: XLSX has 157 via FindKey)."""
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?c) WHERE { ?s a bim:Pipeline }
        """)
        assert count == 147

    def test_adjacency_triple_count(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(*) AS ?c)
            WHERE { ?s bim:adjacentTo ?o }
        """)
        assert count == config.EXPECTED_ADJACENCY_COUNT * 2

    def test_belongs_to_pipeline_count(self, full_graph: Graph) -> None:
        count = _sparql_count(full_graph, """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(*) AS ?c)
            WHERE { ?s bim:belongsToPipeline ?p }
        """)
        assert count == 2926


class TestIntegrationIntegrity:
    """Cross-referential integrity checks."""

    def test_all_typed_objects_sum_to_total(self, full_graph: Graph) -> None:
        """Every object must have exactly one primary type."""
        type_classes = [
            "PipingComponent", "StructuralMember", "ElectricalComponent",
            "HvacComponent", "UncategorizedObject", "HierarchyNode",
            "AnalysisVolume",
        ]
        eqp_classes = [
            "ProcessEquipment", "ElectricalEquipment",
            "ArchitecturalEquipment", "HvacEquipment", "CivilElements",
            "CivilEquipment", "BlackBoxSystems", "UnclassifiedEquipment",
        ]
        total = 0
        for cls in type_classes + eqp_classes:
            count = _sparql_count(full_graph, f"""
                PREFIX bim: <http://example.org/bim-ontology/>
                SELECT (COUNT(?s) AS ?c) WHERE {{ ?s a bim:{cls} }}
            """)
            total += count
        assert total == config.EXPECTED_OBJECT_COUNT

    def test_pipeline_targets_exist_in_shared(self, full_graph: Graph) -> None:
        """Every belongsToPipeline target must be a Pipeline individual."""
        query = """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?p) AS ?c)
            WHERE {
                ?s bim:belongsToPipeline ?p .
                FILTER NOT EXISTS { ?p a bim:Pipeline }
            }
        """
        orphans = _sparql_count(full_graph, query)
        assert orphans == 0

    def test_every_object_has_object_id(self, full_graph: Graph) -> None:
        """Every typed instance must have an objectId data property."""
        query = """
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?c)
            WHERE {
                ?s a ?t .
                ?t rdfs:subClassOf* bim:BIMEntity .
                FILTER NOT EXISTS { ?s bim:objectId ?id }
            }
        """
        missing = _sparql_count(full_graph, query)
        assert missing == 0


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------


class TestGenerateAbox:
    def test_generate_creates_three_files(self, tmp_path: Path) -> None:
        gold = pd.DataFrame({
            "object_id": ["x"],
            "refined_class": ["Piping"],
            "is_analysis_volume": [False],
            "is_container": [False],
            "sp3d_eqp_type_0": [None],
            "title_display_name": ["Test"],
            "system_path": [""],
            "level": [6],
            "centroid_x": [0.0], "centroid_y": [0.0], "centroid_z": [0.0],
            "bbox_volume_m3": [0.0],
            "vertex_count": [10], "triangle_count": [5],
            "has_real_mesh": [True],
            "classification_confidence": ["HIGH"],
            "classification_confidence_reason": ["xlsx_class_clean"],
            "sp3d_pipeline": ["P-001"],
            "sp3d_pipe_run": ["PR-001"],
            "parent_id": [None],
            "sp3d_material": [None],
            "sp3d_spec_name": [None],
            "sp3d_commodity_code": [None],
            "sp3d_npd": [None],
            "group_id": [None],
            "dry_weight_kg": [100.0],
            "wet_weight_kg": [None],
            "length_m": [5.0],
            "design_pressure_kpa": [None],
            "design_temperature_c": [None],
        })
        adj = pd.DataFrame({
            "source_object_id": pd.Series(dtype="str"),
            "target_object_id": pd.Series(dtype="str"),
        })
        paths = generate_abox(gold, adj, tmp_path)
        assert len(paths) == 3
        for name, p in paths.items():
            assert p.exists(), f"{name} not found"
            assert p.stat().st_size > 0
