"""Tests for bimkg.validation (SHACL shapes + validation runner)."""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from bimkg import config
from bimkg.ontology.namespaces import BIM, INST
from bimkg.validation.shapes import build_shapes, generate_shapes
from bimkg.validation.validate import run_validation, ValidationResult


# ---------------------------------------------------------------------------
# Unit: shapes graph
# ---------------------------------------------------------------------------


class TestShapesGraph:
    @pytest.fixture(scope="class")
    def shapes(self) -> Graph:
        return build_shapes()

    def test_has_shapes(self, shapes: Graph) -> None:
        SH = URIRef("http://www.w3.org/ns/shacl#NodeShape")
        node_shapes = list(shapes.subjects(RDF.type, SH))
        assert len(node_shapes) == 6

    def test_piping_pipeline_shape_exists(self, shapes: Graph) -> None:
        shape = BIM["PipingMustHavePipelineShape"]
        assert (shape, RDF.type, None) in shapes

    def test_equipment_name_shape_exists(self, shapes: Graph) -> None:
        shape = BIM["EquipmentMustHaveNameShape"]
        assert (shape, RDF.type, None) in shapes

    def test_weight_shape_exists(self, shapes: Graph) -> None:
        shape = BIM["WeightNonNegativeShape"]
        assert (shape, RDF.type, None) in shapes

    def test_generate_creates_file(self, tmp_path) -> None:
        path = generate_shapes(tmp_path / "test-shapes.ttl")
        assert path.exists()
        g = Graph()
        g.parse(str(path), format="turtle")
        assert len(g) > 50


# ---------------------------------------------------------------------------
# Unit: validation on synthetic data
# ---------------------------------------------------------------------------


class TestValidationSynthetic:
    def _make_graph_with_piping(self, has_pipeline: bool) -> Graph:
        """Create a minimal graph with one PipingComponent."""
        g = Graph()
        g.parse(str(config.ONTOLOGY_OWL), format="turtle")

        obj = INST["test-pipe-001"]
        g.add((obj, RDF.type, BIM.PipingComponent))
        g.add((obj, BIM.objectId, Literal("test-pipe-001")))
        g.add((obj, BIM.displayName, Literal("TestPipe")))
        g.add((obj, BIM.centroidX, Literal(0.0, datatype=XSD.double)))
        g.add((obj, BIM.centroidY, Literal(0.0, datatype=XSD.double)))
        g.add((obj, BIM.centroidZ, Literal(0.0, datatype=XSD.double)))
        g.add((obj, BIM.hasRealMesh, Literal(True, datatype=XSD.boolean)))
        g.add((obj, BIM.classificationConfidence, Literal("HIGH")))

        if has_pipeline:
            pipe = INST["pipeline-P001"]
            g.add((pipe, RDF.type, BIM.Pipeline))
            g.add((obj, BIM.belongsToPipeline, pipe))

        return g

    def test_piping_with_pipeline_conforms(self) -> None:
        data = self._make_graph_with_piping(has_pipeline=True)
        shapes = build_shapes()
        result = run_validation(data, shapes)
        piping_violations = [v for v in result.violations
                             if "pipeline" in v["shape"].lower()]
        assert len(piping_violations) == 0

    def test_piping_without_pipeline_violates(self) -> None:
        data = self._make_graph_with_piping(has_pipeline=False)
        shapes = build_shapes()
        result = run_validation(data, shapes)
        piping_violations = [v for v in result.violations
                             if "pipeline" in v["message"].lower()]
        assert len(piping_violations) >= 1


# ---------------------------------------------------------------------------
# Integration: full ABox validation
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def full_validation() -> ValidationResult:
    for p in [config.ONTOLOGY_OWL, config.ONTOLOGY_SHAPES,
              config.ONTOLOGY_OWL_DIR / "bim-objects.ttl"]:
        if not p.exists():
            pytest.skip(f"File not found: {p}")
    return run_validation()


class TestFullValidation:
    def test_does_not_conform(self, full_validation) -> None:
        assert full_validation.conforms is False

    def test_total_violations_expected(self, full_validation) -> None:
        """M3: fewer physical objects → fewer violations (739 → ~468)."""
        assert 400 <= full_validation.total_violations <= 550

    def test_mesh_violations_dominant(self, full_validation) -> None:
        """M3: parent boxes moved to HierarchyNode → mesh violations drop."""
        mesh = full_validation.by_shape.get("_prop_mesh", 0)
        assert 350 <= mesh <= 450

    def test_pipeline_violations(self, full_validation) -> None:
        pipeline = full_validation.by_shape.get("_prop_pipeline", 0)
        assert 60 <= pipeline <= 80

    def test_no_weight_violations(self, full_validation) -> None:
        weight = full_validation.by_shape.get("_prop_weight", 0)
        assert weight == 0

    def test_no_coord_violations(self, full_validation) -> None:
        coord_keys = [k for k in full_validation.by_shape if "coord" in k.lower()]
        assert sum(full_validation.by_shape.get(k, 0) for k in coord_keys) == 0

    def test_severity_is_violation_only(self, full_validation) -> None:
        assert "Violation" in full_validation.by_severity
