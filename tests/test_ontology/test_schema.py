"""Tests for bimkg.ontology.schema (TBox)."""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from bimkg import config
from bimkg.ontology.namespaces import BIM
from bimkg.ontology.schema import (
    CLASS_HIERARCHY,
    CONTEXT_CLASSES,
    DATA_PROPERTIES,
    EQP_TYPE_0_MAP,
    OBJECT_PROPERTIES,
    REFINED_CLASS_MAP,
    build_tbox,
    generate_tbox,
)


@pytest.fixture(scope="module")
def tbox() -> Graph:
    return build_tbox()


# ---------------------------------------------------------------------------
# Ontology metadata
# ---------------------------------------------------------------------------


class TestOntologyMetadata:
    def test_has_ontology_declaration(self, tbox: Graph) -> None:
        ont = BIM["bim-ontology"]
        assert (ont, RDF.type, OWL.Ontology) in tbox

    def test_has_label(self, tbox: Graph) -> None:
        ont = BIM["bim-ontology"]
        labels = list(tbox.objects(ont, RDFS.label))
        assert len(labels) == 1
        assert "BIM" in str(labels[0])


# ---------------------------------------------------------------------------
# Class hierarchy (D10 sibling structure)
# ---------------------------------------------------------------------------


class TestClassHierarchy:
    def test_total_class_count(self, tbox: Graph) -> None:
        classes = set(tbox.subjects(RDF.type, OWL.Class))
        expected = len(CLASS_HIERARCHY) + len(CONTEXT_CLASSES)
        assert len(classes) == expected

    def test_bim_entity_is_root(self, tbox: Graph) -> None:
        parents = list(tbox.objects(BIM.BIMEntity, RDFS.subClassOf))
        assert parents == []

    def test_bim_object_under_bim_entity(self, tbox: Graph) -> None:
        assert (BIM.BIMObject, RDFS.subClassOf, BIM.BIMEntity) in tbox

    def test_analysis_artifact_under_bim_entity(self, tbox: Graph) -> None:
        assert (BIM.AnalysisArtifact, RDFS.subClassOf, BIM.BIMEntity) in tbox

    def test_bim_object_and_analysis_artifact_are_siblings(
        self, tbox: Graph
    ) -> None:
        bim_parents = set(tbox.objects(BIM.BIMObject, RDFS.subClassOf))
        aa_parents = set(tbox.objects(BIM.AnalysisArtifact, RDFS.subClassOf))
        assert bim_parents == aa_parents == {BIM.BIMEntity}

    def test_physical_object_under_bim_object(self, tbox: Graph) -> None:
        assert (BIM.PhysicalObject, RDFS.subClassOf, BIM.BIMObject) in tbox

    def test_six_physical_subclasses(self, tbox: Graph) -> None:
        children = set(tbox.subjects(RDFS.subClassOf, BIM.PhysicalObject))
        expected = {
            BIM.PipingComponent,
            BIM.StructuralMember,
            BIM.Equipment,
            BIM.ElectricalComponent,
            BIM.HvacComponent,
            BIM.UncategorizedObject,
        }
        assert children == expected

    def test_container_under_bim_object(self, tbox: Graph) -> None:
        assert (BIM.Container, RDFS.subClassOf, BIM.BIMObject) in tbox

    def test_analysis_volume_under_analysis_artifact(
        self, tbox: Graph
    ) -> None:
        assert (
            BIM.AnalysisVolume,
            RDFS.subClassOf,
            BIM.AnalysisArtifact,
        ) in tbox


# ---------------------------------------------------------------------------
# Equipment subclasses (Q2-C)
# ---------------------------------------------------------------------------


class TestEquipmentSubclasses:
    def test_eight_equipment_subclasses(self, tbox: Graph) -> None:
        children = set(tbox.subjects(RDFS.subClassOf, BIM.Equipment))
        assert len(children) == 8

    def test_unclassified_equipment_exists(self, tbox: Graph) -> None:
        assert (
            BIM.UnclassifiedEquipment,
            RDFS.subClassOf,
            BIM.Equipment,
        ) in tbox

    def test_eqp_type_0_map_covers_all_subclasses_except_unclassified(
        self,
    ) -> None:
        assert len(EQP_TYPE_0_MAP) == 7
        for owl_name in EQP_TYPE_0_MAP.values():
            assert (owl_name, "Equipment") in [
                (name, parent) for name, parent in CLASS_HIERARCHY
            ]


# ---------------------------------------------------------------------------
# Context classes
# ---------------------------------------------------------------------------


class TestContextClasses:
    def test_pipeline_class_exists(self, tbox: Graph) -> None:
        assert (BIM.Pipeline, RDF.type, OWL.Class) in tbox

    def test_pipe_run_class_exists(self, tbox: Graph) -> None:
        assert (BIM.PipeRun, RDF.type, OWL.Class) in tbox

    def test_context_hierarchy(self, tbox: Graph) -> None:
        assert (BIM.Pipeline, RDFS.subClassOf, BIM.Context) in tbox
        assert (BIM.PipeRun, RDFS.subClassOf, BIM.Context) in tbox
        assert (BIM.Level, RDFS.subClassOf, BIM.Context) in tbox
        assert (BIM.Material, RDFS.subClassOf, BIM.Context) in tbox


# ---------------------------------------------------------------------------
# Object properties
# ---------------------------------------------------------------------------


class TestObjectProperties:
    def test_object_property_count(self, tbox: Graph) -> None:
        props = set(tbox.subjects(RDF.type, OWL.ObjectProperty))
        assert len(props) == len(OBJECT_PROPERTIES)

    def test_adjacent_to_is_symmetric(self, tbox: Graph) -> None:
        assert (BIM.adjacentTo, RDF.type, OWL.SymmetricProperty) in tbox

    def test_adjacent_to_domain_range(self, tbox: Graph) -> None:
        assert (BIM.adjacentTo, RDFS.domain, BIM.PhysicalObject) in tbox
        assert (BIM.adjacentTo, RDFS.range, BIM.PhysicalObject) in tbox

    def test_belongs_to_pipeline(self, tbox: Graph) -> None:
        assert (
            BIM.belongsToPipeline,
            RDFS.domain,
            BIM.PipingComponent,
        ) in tbox
        assert (
            BIM.belongsToPipeline,
            RDFS.range,
            BIM.Pipeline,
        ) in tbox

    def test_has_parent_is_general(self, tbox: Graph) -> None:
        assert (BIM.hasParent, RDFS.domain, BIM.BIMEntity) in tbox
        assert (BIM.hasParent, RDFS.range, BIM.BIMEntity) in tbox


# ---------------------------------------------------------------------------
# Data properties
# ---------------------------------------------------------------------------


class TestDataProperties:
    def test_data_property_count(self, tbox: Graph) -> None:
        props = set(tbox.subjects(RDF.type, OWL.DatatypeProperty))
        assert len(props) == len(DATA_PROPERTIES)

    def test_object_id_is_string(self, tbox: Graph) -> None:
        assert (BIM.objectId, RDFS.range, XSD.string) in tbox

    def test_dry_weight_is_double(self, tbox: Graph) -> None:
        assert (BIM.dryWeightKg, RDFS.range, XSD.double) in tbox
        assert (BIM.dryWeightKg, RDFS.domain, BIM.PhysicalObject) in tbox

    def test_classification_confidence_exists(self, tbox: Graph) -> None:
        assert (
            BIM.classificationConfidence,
            RDF.type,
            OWL.DatatypeProperty,
        ) in tbox

    def test_level_is_integer(self, tbox: Graph) -> None:
        assert (BIM.level, RDFS.range, XSD.integer) in tbox

    def test_has_real_mesh_is_boolean(self, tbox: Graph) -> None:
        assert (BIM.hasRealMesh, RDFS.range, XSD.boolean) in tbox


# ---------------------------------------------------------------------------
# Mapping constants
# ---------------------------------------------------------------------------


class TestMappingConstants:
    def test_refined_class_map_covers_all_six_classes(self) -> None:
        expected = {"Piping", "Structure", "Equipment", "Electrical", "HVAC", "Other"}
        assert set(REFINED_CLASS_MAP.keys()) == expected

    def test_refined_class_map_values_are_valid_classes(self) -> None:
        class_names = {name for name, _ in CLASS_HIERARCHY}
        for owl_name in REFINED_CLASS_MAP.values():
            assert owl_name in class_names, f"{owl_name} not in hierarchy"


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------


class TestFileGeneration:
    def test_generate_tbox_creates_file(self, tmp_path) -> None:
        out = generate_tbox(tmp_path / "test-ontology.owl")
        assert out.exists()
        assert out.stat().st_size > 0

    def test_generated_file_is_valid_turtle(self, tmp_path) -> None:
        out = generate_tbox(tmp_path / "test-ontology.owl")
        g = Graph()
        g.parse(str(out), format="turtle")
        assert len(g) > 200

    def test_roundtrip_preserves_class_count(self, tmp_path) -> None:
        out = generate_tbox(tmp_path / "test-ontology.owl")
        g = Graph()
        g.parse(str(out), format="turtle")
        classes = set(g.subjects(RDF.type, OWL.Class))
        expected = len(CLASS_HIERARCHY) + len(CONTEXT_CLASSES)
        assert len(classes) == expected
