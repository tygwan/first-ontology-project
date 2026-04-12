"""SHACL shape definitions for BIM data quality validation.

Each shape is a data quality rule expressed as a SHACL NodeShape.
Running these shapes against the ABox produces a structured validation
report — violations are data quality issues to investigate.

Shapes are organized by severity:
- ERROR: must-fix issues (structural integrity)
- WARNING: should-investigate (data completeness)
- INFO: advisory (best-practice)
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD, OWL

from bimkg import config
from bimkg.ontology.namespaces import BIM, NAMESPACE_BINDINGS

SH = Namespace("http://www.w3.org/ns/shacl#")


def build_shapes() -> Graph:
    """Build the SHACL shapes graph."""
    g = Graph()
    for prefix, ns in NAMESPACE_BINDINGS.items():
        g.bind(prefix, ns)
    g.bind("sh", SH)

    _piping_must_have_pipeline(g)
    _equipment_must_have_name(g)
    _physical_must_have_mesh(g)
    _weight_non_negative(g)
    _object_must_have_coords(g)
    _piping_confidence_check(g)

    return g


# ---------------------------------------------------------------------------
# Shape builders
# ---------------------------------------------------------------------------


def _piping_must_have_pipeline(g: Graph) -> None:
    """ERROR: Every PipingComponent must belong to a Pipeline."""
    shape = BIM["PipingMustHavePipelineShape"]
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, BIM.PipingComponent))
    g.add((shape, SH.severity, SH.Violation))
    g.add((shape, RDFS.label, Literal("Piping must belong to a Pipeline")))
    g.add((shape, SH.description, Literal(
        "Every PipingComponent should have at least one belongsToPipeline link. "
        "Violations indicate piping objects not assigned to any pipeline."
    )))

    prop = BIM["_prop_pipeline"]
    g.add((shape, SH.property, prop))
    g.add((prop, SH.path, BIM.belongsToPipeline))
    g.add((prop, SH.minCount, Literal(1)))
    g.add((prop, SH.message, Literal("PipingComponent has no belongsToPipeline link")))


def _equipment_must_have_name(g: Graph) -> None:
    """WARNING: Every Equipment should have a displayName."""
    shape = BIM["EquipmentMustHaveNameShape"]
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, BIM.Equipment))
    g.add((shape, SH.severity, SH.Warning))
    g.add((shape, RDFS.label, Literal("Equipment must have a display name")))

    prop = BIM["_prop_eqp_name"]
    g.add((shape, SH.property, prop))
    g.add((prop, SH.path, BIM.displayName))
    g.add((prop, SH.minCount, Literal(1)))
    g.add((prop, SH.message, Literal("Equipment has no displayName")))

    # Also target all Equipment subclasses via implicit class targeting
    for subcls in [
        "ProcessEquipment", "ElectricalEquipment", "ArchitecturalEquipment",
        "HvacEquipment", "CivilElements", "CivilEquipment",
        "BlackBoxSystems", "UnclassifiedEquipment",
    ]:
        g.add((shape, SH.targetClass, BIM[subcls]))


def _physical_must_have_mesh(g: Graph) -> None:
    """WARNING: PhysicalObject should have hasRealMesh = true."""
    shape = BIM["PhysicalMustHaveMeshShape"]
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, BIM.PhysicalObject))
    g.add((shape, SH.severity, SH.Warning))
    g.add((shape, RDFS.label, Literal("Physical object should have real mesh")))

    prop = BIM["_prop_mesh"]
    g.add((shape, SH.property, prop))
    g.add((prop, SH.path, BIM.hasRealMesh))
    g.add((prop, SH.hasValue, Literal(True, datatype=XSD.boolean)))
    g.add((prop, SH.message, Literal("PhysicalObject has no real mesh (hasRealMesh != true)")))

    # Target all PhysicalObject subclasses
    for subcls in [
        "PipingComponent", "StructuralMember", "Equipment",
        "ElectricalComponent", "HvacComponent", "UncategorizedObject",
    ]:
        g.add((shape, SH.targetClass, BIM[subcls]))


def _weight_non_negative(g: Graph) -> None:
    """ERROR: dryWeightKg must be >= 0 when present."""
    shape = BIM["WeightNonNegativeShape"]
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, BIM.PhysicalObject))
    g.add((shape, SH.severity, SH.Violation))
    g.add((shape, RDFS.label, Literal("Weight must be non-negative")))

    prop = BIM["_prop_weight"]
    g.add((shape, SH.property, prop))
    g.add((prop, SH.path, BIM.dryWeightKg))
    g.add((prop, SH.minInclusive, Literal(0.0, datatype=XSD.double)))
    g.add((prop, SH.message, Literal("dryWeightKg is negative")))

    for subcls in [
        "PipingComponent", "StructuralMember", "Equipment",
        "ElectricalComponent", "HvacComponent", "UncategorizedObject",
    ]:
        g.add((shape, SH.targetClass, BIM[subcls]))


def _object_must_have_coords(g: Graph) -> None:
    """ERROR: Every BIMEntity must have centroid coordinates."""
    shape = BIM["ObjectMustHaveCoordsShape"]
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, BIM.BIMEntity))
    g.add((shape, SH.severity, SH.Violation))
    g.add((shape, RDFS.label, Literal("Object must have centroid coordinates")))

    for coord_prop in [BIM.centroidX, BIM.centroidY, BIM.centroidZ]:
        prop_node = BIM[f"_prop_coord_{coord_prop.split('/')[-1]}"]
        g.add((shape, SH.property, prop_node))
        g.add((prop_node, SH.path, coord_prop))
        g.add((prop_node, SH.minCount, Literal(1)))
        g.add((prop_node, SH.datatype, XSD.double))
        g.add((prop_node, SH.message, Literal(f"Missing coordinate: {coord_prop.split('/')[-1]}")))


def _piping_confidence_check(g: Graph) -> None:
    """INFO: PipingComponent with pipeline should have HIGH confidence."""
    shape = BIM["PipingConfidenceShape"]
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, BIM.PipingComponent))
    g.add((shape, SH.severity, SH.Info))
    g.add((shape, RDFS.label, Literal("Piping with pipeline should be HIGH confidence")))

    prop = BIM["_prop_confidence"]
    g.add((shape, SH.property, prop))
    g.add((prop, SH.path, BIM.classificationConfidence))
    g.add((prop, SH.minCount, Literal(1)))
    g.add((prop, SH.message, Literal("PipingComponent missing classificationConfidence")))


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------


def generate_shapes(output_path: Path | None = None) -> Path:
    """Generate the SHACL shapes file and return its path."""
    if output_path is None:
        output_path = config.ONTOLOGY_SHAPES
    output_path.parent.mkdir(parents=True, exist_ok=True)

    g = build_shapes()
    g.serialize(destination=str(output_path), format="turtle")
    return output_path
